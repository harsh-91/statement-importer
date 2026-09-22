# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import threading
import ctypes
from ctypes import wintypes
import os
import sys
import json
import webbrowser

import webview
import psycopg
from werkzeug.serving import make_server

from app import app
from statement_importer.config import ConfigError
from statement_importer.access import get_setting
from statement_importer.database import ensure_schema
from statement_importer.local_postgres import LocalPostgresError, start_managed_postgres_if_present
from statement_importer.updater import start_background_check


_mutex_handle = None
_shutdown_event_handle = None
SHUTDOWN_EVENT_NAME = "Local\\StatementImporterShutdown"
EVENT_MODIFY_STATE = 0x0002
INFINITE = 0xFFFFFFFF


def windows_api():
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.SetEvent.argtypes = (wintypes.HANDLE,)
    kernel32.SetEvent.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    return kernel32


def acquire_single_instance() -> bool:
    global _mutex_handle
    if not hasattr(ctypes, "windll"):
        return True
    _mutex_handle = windows_api().CreateMutexW(None, False, "Local\\StatementImporterDesktop")
    return bool(_mutex_handle) and ctypes.windll.kernel32.GetLastError() != 183


def signal_running_instance_shutdown() -> bool:
    if not hasattr(ctypes, "windll"):
        return False
    kernel32 = windows_api()
    kernel32.OpenEventW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.OpenEventW.restype = wintypes.HANDLE
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, SHUTDOWN_EVENT_NAME)
    if not handle:
        return False
    try:
        return bool(kernel32.SetEvent(handle))
    finally:
        kernel32.CloseHandle(handle)


def start_shutdown_listener(server: "LocalServer") -> None:
    global _shutdown_event_handle
    if not hasattr(ctypes, "windll"):
        return
    kernel32 = windows_api()
    kernel32.CreateEventW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateEventW.restype = wintypes.HANDLE
    _shutdown_event_handle = kernel32.CreateEventW(None, True, False, SHUTDOWN_EVENT_NAME)
    if not _shutdown_event_handle:
        return

    def wait_for_installer() -> None:
        if kernel32.WaitForSingleObject(_shutdown_event_handle, INFINITE) != 0:
            return
        server.stop()
        os._exit(0)

    threading.Thread(target=wait_for_installer, name="installer-shutdown", daemon=True).start()


class LocalServer:
    def __init__(self):
        self.server = make_server("127.0.0.1", 8765, app, threaded=True)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()


def main():
    if "--shutdown" in sys.argv:
        signal_running_instance_shutdown()
        return
    if not acquire_single_instance():
        webbrowser.open("http://127.0.0.1:8765")
        return
    server = LocalServer()
    server.start()
    start_shutdown_listener(server)
    try:
        window = webview.create_window(
            "Statement Importer",
            html='''<!doctype html><html><body style="background:#101524;color:#bafbe0;font:20px monospace;padding:48px">
                <h1>Statement Importer</h1><p id="stage">Opening your workspace...</p>
                <progress></progress><p id="elapsed">Starting...</p>
                <p>Your database may take a minute to start.</p>
                <script>let seconds=0;setInterval(()=>document.getElementById('elapsed').textContent=
                'Elapsed: '+(++seconds)+' seconds',1000);</script></body></html>''',
            width=1020,
            height=820,
            min_size=(760, 620),
            background_color="#f4f6f8",
        )
        def initialize():
            def show(message):
                try:
                    window.evaluate_js('document.getElementById("stage").textContent=' + json.dumps(message))
                except Exception:
                    pass
            try:
                show("Starting your local database...")
                start_managed_postgres_if_present()
                show("Checking your database and tables...")
                ensure_schema()
                start_background_check(bool(get_setting("automatic_update_checks", False)))
                window.load_url("http://127.0.0.1:8765/")
            except Exception:
                app.config["STARTUP_ERROR"] = "Your database is not ready yet. Choose local storage below, or check your existing server settings."
                window.load_url("http://127.0.0.1:8765/setup")
        webview.start(initialize)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
