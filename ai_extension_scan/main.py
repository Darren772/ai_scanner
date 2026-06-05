"""
renScan — entry point.

Boot sequence:
  1. Load settings from config/settings.py
  2. Set CTk appearance mode and colour theme
  3. Create CTk root window
  4. Build main dashboard window (ui/main_window.py)
  5. Register global hotkey via core/hotkey.py
  6. Start system tray icon via ui/tray.py
  7. Keep main thread alive via CTk mainloop

Hotkey callback flow:
  on_hotkey_trigger()
    -> main_window.hide()          (so screen is clear for selection)
    -> ui/overlay.py show()
      -> on_select(x, y, w, h)
        -> core/capture.py capture_region()
        -> ui/results_panel.py show_loading()
        -> core/checker.py run()          [runs in background thread]
          -> api/client.py get_provider().send()
          -> history/log.py append()      [if save_history is on]
          -> core/capture.py delete_temp() [if privacy_mode is on]
        -> ui/results_panel.py show(result)
        -> main_window.refresh_home()
"""

import threading
import customtkinter as ctk

from config import settings as settings_module
from core import hotkey, capture, checker
from ui import overlay, results_panel
from ui.main_window import MainWindow
from ui import tray
from utils import logger


# ── Globals ─────────────────────────────────────────────────────────────────
_settings:     dict        = {}
_tray_icon                 = None
_root:         ctk.CTk     = None
_main_window:  MainWindow  = None


# ── Hotkey / capture callbacks ───────────────────────────────────────────────

def on_hotkey_trigger() -> None:
    """Called (from background keyboard thread) when the global hotkey fires."""
    logger.info("Hotkey triggered")
    _root.after(0, _launch_overlay)


def _launch_overlay() -> None:
    """Hide the main window so the screen is clear, then open overlay."""
    # Check concurrent scans limit
    max_scans = _settings.get("max_concurrent_scans", 3)
    if results_panel.ResultsPanel._open_count >= max_scans:
        logger.warning(f"Concurrent scan limit reached ({max_scans}). Ignoring hotkey.")
        # Restore main window in case it was hidden by clicking 'Scan Now' button
        _main_window.show()
        return

    # Prevent launching a duplicate overlay if one is already open
    if overlay._active:
        return
    
    # Remember if the window was visible so we can restore it on cancel
    was_visible = _root.state() != "withdrawn"
    _main_window.hide()

    def _on_overlay_cancel() -> None:
        if was_visible:
            _main_window.show()

    overlay.show(on_select, on_cancel=_on_overlay_cancel)


def on_select(x: int, y: int, w: int, h: int) -> None:
    """Called after the user releases the mouse on the overlay."""
    logger.info(f"Region selected: ({x}, {y})  {w}×{h}")
    
    # Instantiate a new results panel for this scan
    panel = results_panel.ResultsPanel()
    panel.show_loading()

    def _run_check() -> None:
        img_path: str | None = None
        try:
            img_path = capture.capture_region(x, y, w, h)
            mode     = _settings.get("check_mode", "full")
            result   = checker.run(img_path, mode)

            if _settings.get("privacy_mode", True):
                capture.delete_temp(img_path)
                img_path = None

            def _safe_show(r=result):
                if panel.winfo_exists():
                    panel.show(r)

            _root.after(0, _safe_show)
            _root.after(0, _main_window.refresh_home)   # update stats on home panel
            logger.info("Check complete")

        except Exception as exc:
            logger.error(f"Check failed: {exc}")
            if img_path and _settings.get("privacy_mode", True):
                capture.delete_temp(img_path)

            def _safe_error(e=str(exc)):
                if panel.winfo_exists():
                    panel.show_error(e)

            _root.after(0, _safe_error)

    threading.Thread(target=_run_check, daemon=True).start()


# ── Tray callbacks ───────────────────────────────────────────────────────────

def on_toggle_window() -> None:
    _root.after(0, _main_window.toggle)

def on_open_settings() -> None:
    _root.after(0, lambda: _main_window.navigate("settings"))

def on_open_history() -> None:
    _root.after(0, lambda: _main_window.navigate("history"))

def on_quit() -> None:
    logger.info("Quitting renScan")
    hotkey.unregister_all()
    if _tray_icon:
        try:
            _tray_icon.stop()
        except Exception:
            pass
    _root.after(0, _root.quit)


# ── Boot ─────────────────────────────────────────────────────────────────────

def main() -> None:
    global _settings, _tray_icon, _root, _main_window

    # 1. Load settings
    _settings = settings_module.load()

    # 2. CTk theming (must happen before any CTk window)
    ctk.set_appearance_mode(_settings.get("appearance_mode", "system"))
    ctk.set_default_color_theme(_settings.get("color_theme", "blue"))

    # 3. Create root window
    _root = ctk.CTk()

    # 4. Build main dashboard window
    _main_window = MainWindow(_root, on_scan=on_hotkey_trigger)

    # 5. Register hotkey
    hk = _settings.get("hotkey", "ctrl+shift+s")
    hotkey.register(hk, on_hotkey_trigger)
    logger.info(f"Hotkey registered: {hk}")

    # 6. Start tray
    _tray_icon = tray.start(
        on_settings=on_open_settings,
        on_history=on_open_history,
        on_quit=on_quit,
        on_toggle=on_toggle_window,
    )
    logger.info("renScan started")

    # 7. Main loop
    _root.mainloop()


if __name__ == "__main__":
    main()
