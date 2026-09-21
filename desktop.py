# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import threading
import ctypes
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


def acquire_single_instance() -> bool:
    global _mutex_handle
    if not hasattr(ctypes, "windll"):
        return True
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\StatementImporterDesktop")
    return bool(_mutex_handle) and ctypes.windll.kernel32.GetLastError() != 183


class LocalServer:
    def __init__(self):
        self.server = make_server("127.0.0.1", 8765, app)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()


def main():
    if not acquire_single_instance():
        webbrowser.open("http://127.0.0.1:8765")
        return
    try:
        start_managed_postgres_if_present()
    except LocalPostgresError:
        pass
    database_ready = False
    try:
        ensure_schema()
        database_ready = True
    except (ConfigError, psycopg.Error):
        pass
    if database_ready:
        try:
            start_background_check(bool(get_setting("automatic_update_checks", False)))
        except (ConfigError, psycopg.Error):
            pass
    server = LocalServer()
    server.start()
    try:
        webview.create_window(
            "Statement Importer",
            "http://127.0.0.1:8765",
            width=1020,
            height=820,
            min_size=(760, 620),
            background_color="#f4f6f8",
        )
        webview.start()
    finally:
        server.stop()


if __name__ == "__main__":
    main()
