"""
Add or remove renScan from OS startup.

Windows  -> batch script in %APPDATA%/Microsoft/Windows/Start Menu/Programs/Startup
macOS    -> launchd plist in ~/Library/LaunchAgents/com.renscan.plist
Linux    -> .desktop file in ~/.config/autostart/renscan.desktop
"""

import os
import sys


# ── Helpers ────────────────────────────────────────────────────────────────

def _main_py_path() -> str:
    """Absolute path to this project's main.py."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
    )


# ── Windows ────────────────────────────────────────────────────────────────

def _win_bat_path() -> str:
    startup = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )
    return os.path.join(startup, "renScan.bat")


def _win_enable() -> None:
    path = _win_bat_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f'@echo off\nstart "" "{sys.executable}" "{_main_py_path()}"\n')


def _win_disable() -> None:
    path = _win_bat_path()
    if os.path.exists(path):
        os.remove(path)


def _win_is_enabled() -> bool:
    return os.path.exists(_win_bat_path())


# ── macOS ─────────────────────────────────────────────────────────────────

def _mac_plist_path() -> str:
    return os.path.expanduser("~/Library/LaunchAgents/com.renscan.plist")


def _mac_enable() -> None:
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.renscan</string>
  <key>ProgramArguments</key>
  <array>
    <string>{sys.executable}</string>
    <string>{_main_py_path()}</string>
  </array>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
"""
    path = _mac_plist_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(plist)


def _mac_disable() -> None:
    path = _mac_plist_path()
    if os.path.exists(path):
        os.remove(path)


def _mac_is_enabled() -> bool:
    return os.path.exists(_mac_plist_path())


# ── Linux ─────────────────────────────────────────────────────────────────

def _linux_desktop_path() -> str:
    return os.path.expanduser("~/.config/autostart/renscan.desktop")


def _linux_enable() -> None:
    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=renScan\n"
        f"Exec={sys.executable} {_main_py_path()}\n"
        "Hidden=false\n"
        "NoDisplay=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    path = _linux_desktop_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(desktop)


def _linux_disable() -> None:
    path = _linux_desktop_path()
    if os.path.exists(path):
        os.remove(path)


def _linux_is_enabled() -> bool:
    return os.path.exists(_linux_desktop_path())


# ── Public API ─────────────────────────────────────────────────────────────

def enable() -> None:
    """Register renScan to launch at OS startup."""
    if sys.platform == "win32":
        _win_enable()
    elif sys.platform == "darwin":
        _mac_enable()
    else:
        _linux_enable()


def disable() -> None:
    """Remove renScan from OS startup."""
    if sys.platform == "win32":
        _win_disable()
    elif sys.platform == "darwin":
        _mac_disable()
    else:
        _linux_disable()


def is_enabled() -> bool:
    """Return True if renScan is currently set to launch at startup."""
    if sys.platform == "win32":
        return _win_is_enabled()
    elif sys.platform == "darwin":
        return _mac_is_enabled()
    else:
        return _linux_is_enabled()
