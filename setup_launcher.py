# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import winreg
from pathlib import Path
from tkinter import BOTH, END, LEFT, X, Button, Entry, Frame, Label, Listbox, StringVar, Tk, filedialog, messagebox


APP_NAME = "Statement Importer"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / "StatementImporter"
APP_EXE = INSTALL_DIR / "StatementImporter.exe"
UNINSTALL_EXE = INSTALL_DIR / "Uninstall.exe"


def resource(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def postgres_installations() -> list[str]:
    roots = [Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PostgreSQL"]
    found = []
    for root in roots:
        if root.exists():
            for executable in root.glob("*/bin/postgres.exe"):
                found.append(str(executable.parent.parent))
    return sorted(found, reverse=True)


def webview2_installations() -> list[str]:
    roots = [
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/EdgeWebView/Application",
        Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Microsoft/EdgeWebView/Application",
    ]
    found = []
    for root in roots:
        if root.exists():
            found.extend(str(path.parent) for path in root.glob("*/msedgewebview2.exe"))
    return sorted(set(found), reverse=True)


def supported_platform() -> tuple[bool, str]:
    machine = platform.machine().lower()
    if os.name != "nt":
        return False, "This release is for Windows only."
    if machine not in {"amd64", "x86_64"}:
        return False, f"This release requires 64-bit Intel/AMD Windows; detected {machine or 'unknown'}."
    if int(platform.version().split(".")[-1]) < 17763:
        return False, "Windows 10 build 17763 or newer is required."
    return True, "Windows 10/11 x64 compatible"


def create_shortcut(shortcut: Path, target: Path) -> None:
    shortcut.parent.mkdir(parents=True, exist_ok=True)
    escape = lambda value: str(value).replace("'", "''")
    command = (
        "$w=New-Object -ComObject WScript.Shell;"
        f"$s=$w.CreateShortcut('{escape(shortcut)}');"
        f"$s.TargetPath='{escape(target)}';$s.WorkingDirectory='{escape(INSTALL_DIR)}';"
        f"$s.IconLocation='{escape(target)},0';$s.Save()"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], check=True, creationflags=0x08000000)


def register_uninstaller() -> None:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\StatementImporter"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.3.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Harsh - Made in India")
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(APP_EXE))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{UNINSTALL_EXE}" --uninstall')
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)


def uninstall() -> None:
    if not messagebox.askyesno(APP_NAME, "Remove the application? PostgreSQL and imported data will be preserved."):
        return
    desktop = Path.home() / "Desktop" / "Statement Importer.lnk"
    menu = Path(os.environ.get("APPDATA", Path.home())) / "Microsoft/Windows/Start Menu/Programs/Statement Importer.lnk"
    for path in (desktop, menu):
        if path.exists():
            path.unlink()
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\StatementImporter")
    except FileNotFoundError:
        pass
    cleanup = INSTALL_DIR / "remove-after-exit.cmd"
    cleanup.write_text(f'@echo off\r\nping 127.0.0.1 -n 3 >nul\r\nrmdir /s /q "{INSTALL_DIR}"\r\n', encoding="utf-8")
    subprocess.Popen(["cmd.exe", "/c", str(cleanup)], creationflags=0x08000000)
    raise SystemExit(0)


class SetupWindow:
    def __init__(self):
        self.root = Tk()
        self.root.title("Statement Importer // Setup")
        self.root.geometry("800x680")
        self.root.minsize(720, 600)
        self.root.configure(bg="#050812")
        self.status = StringVar()
        self._build()
        self.refresh()

    def label(self, parent, text="", **kwargs):
        return Label(parent, text=text, bg="#050812", fg=kwargs.pop("fg", "#54f7ff"),
                     font=kwargs.pop("font", ("Consolas", 11)), **kwargs)

    def _build(self):
        self.label(self.root, "STATEMENT_IMPORTER_SETUP_", font=("Consolas", 14, "bold")).pack(anchor="w", padx=28, pady=(24, 5))
        self.label(self.root, "OFFLINE-FIRST WINDOWS INSTALLER", fg="#74ff80", font=("Consolas", 9)).pack(anchor="w", padx=28)
        self.label(self.root, "INSTALL APPLICATION + CHECK POSTGRESQL", fg="#e7fbff", font=("Consolas", 22, "bold")).pack(anchor="w", padx=28, pady=(30, 8))
        self.label(self.root, "No statement data, passwords, or telemetry leave this computer.", fg="#8aa0b8").pack(anchor="w", padx=28)
        panel = Frame(self.root, bg="#0a1020", highlightbackground="#263958", highlightthickness=2)
        panel.pack(fill=BOTH, expand=True, padx=28, pady=24)
        self.label(panel, "POSTGRESQL DETECTION", font=("Consolas", 12, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        self.listbox = Listbox(panel, bg="#030711", fg="#74ff80", selectbackground="#172b50", borderwidth=0, font=("Consolas", 10), height=5)
        self.listbox.pack(fill=X, padx=18)
        self.label(panel, textvariable=self.status, fg="#ffd75a").pack(anchor="w", padx=18, pady=10)
        actions = Frame(panel, bg="#0a1020")
        actions.pack(fill=X, padx=18, pady=6)
        self.button(actions, "REFRESH", self.refresh).pack(side=LEFT, padx=(0, 8))
        self.button(actions, "INSTALL POSTGRESQL WITH WINGET", self.install_postgres).pack(side=LEFT, padx=8)
        self.button(actions, "RUN DOWNLOADED INSTALLER", self.choose_installer).pack(side=LEFT, padx=8)
        self.button(panel, "INSTALL WEBVIEW2 WITH WINGET", self.install_webview).pack(anchor="w", padx=18, pady=(8, 2))
        self.label(panel, "Internet is needed only for the optional winget download. You may download PostgreSQL yourself and select its installer here.", fg="#8aa0b8", wraplength=650, justify=LEFT).pack(anchor="w", padx=18, pady=(12, 4))
        self.button(panel, "INSTALL + LAUNCH STATEMENT IMPORTER", self.install_app, primary=True).pack(anchor="w", padx=18, pady=18)

    def button(self, parent, text, command, primary=False):
        return Button(parent, text=text, command=command, bg="#54f7ff" if primary else "#172b50",
                      fg="#050812" if primary else "#e7fbff", activebackground="#74ff80",
                      relief="flat", padx=12, pady=9, font=("Consolas", 9, "bold"), cursor="hand2")

    def refresh(self):
        self.listbox.delete(0, END)
        installations = postgres_installations()
        for item in installations:
            self.listbox.insert(END, f"[FOUND] {item}")
        webviews = webview2_installations()
        for item in webviews:
            self.listbox.insert(END, f"[WEBVIEW2] {item}")
        supported, message = supported_platform()
        database = "POSTGRESQL READY" if installations else "POSTGRESQL NOT DETECTED"
        browser = "WEBVIEW2 READY" if webviews else "WEBVIEW2 NOT DETECTED"
        self.status.set(f"{message.upper()} // {database} // {browser}")

    def install_postgres(self):
        if not shutil.which("winget"):
            messagebox.showerror(APP_NAME, "winget is unavailable. Download PostgreSQL manually and use RUN DOWNLOADED INSTALLER.")
            return
        if not messagebox.askyesno(APP_NAME, "Download and run the PostgreSQL 17 installer using winget? Internet access is required."):
            return
        subprocess.Popen(["winget", "install", "--exact", "--id", "PostgreSQL.PostgreSQL.17",
                          "--accept-package-agreements", "--accept-source-agreements"])
        self.status.set("POSTGRESQL INSTALLER STARTED // REFRESH WHEN COMPLETE")

    def choose_installer(self):
        path = filedialog.askopenfilename(title="Select PostgreSQL installer", filetypes=[("Windows installer", "*.exe")])
        if path:
            subprocess.Popen([path])
            self.status.set("MANUAL INSTALLER STARTED // REFRESH WHEN COMPLETE")

    def install_webview(self):
        if not shutil.which("winget"):
            messagebox.showerror(APP_NAME, "winget is unavailable. Install Microsoft Edge WebView2 Runtime manually.")
            return
        subprocess.Popen(["winget", "install", "--exact", "--id", "Microsoft.EdgeWebView2Runtime",
                          "--accept-package-agreements", "--accept-source-agreements"])
        self.status.set("WEBVIEW2 INSTALLER STARTED // REFRESH WHEN COMPLETE")

    def install_app(self):
        supported, message = supported_platform()
        if not supported:
            messagebox.showerror(APP_NAME, message)
            return
        if not webview2_installations() and not messagebox.askyesno(
            APP_NAME, "WebView2 was not detected. Continue anyway? The app window may not open until it is installed."
        ):
            return
        payload = resource("payload/StatementImporter.exe")
        if not payload.exists():
            messagebox.showerror(APP_NAME, "The setup payload is missing.")
            return
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(payload, APP_EXE)
        shutil.copy2(sys.executable, UNINSTALL_EXE)
        for document in ("QUICK_START.txt", "LICENSE.md"):
            source = resource(f"payload/{document}")
            if source.exists():
                shutil.copy2(source, INSTALL_DIR / document)
        create_shortcut(Path.home() / "Desktop" / "Statement Importer.lnk", APP_EXE)
        create_shortcut(Path(os.environ.get("APPDATA", Path.home())) / "Microsoft/Windows/Start Menu/Programs/Statement Importer.lnk", APP_EXE)
        register_uninstaller()
        subprocess.Popen([str(APP_EXE)], cwd=INSTALL_DIR)
        messagebox.showinfo(APP_NAME, "Installation complete. Choose automatic local setup when the application opens.")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    root = Tk()
    root.withdraw()
    if "--uninstall" in sys.argv:
        uninstall()
    root.destroy()
    SetupWindow().run()
