"""
Registers global hotkeys using the `keyboard` library (runs in background thread).

Hotkeys:
  <configured hotkey>  -> trigger overlay
  Esc                  -> cancel overlay / close results panel  (handled in UI)
  Ctrl+C               -> copy last result to clipboard (handled in UI)
  Ctrl+Shift+H         -> open history window (optional secondary hotkey)
"""

import threading
import keyboard as _keyboard

_registered: list[str] = []
_hook = None


def register(hotkey: str, on_trigger) -> None:
    """
    Start listening for `hotkey`. Calls on_trigger() when it fires.
    Runs in a daemon thread so it never blocks the main loop.
    """
    global _hook

    def _listen() -> None:
        _keyboard.add_hotkey(hotkey, on_trigger, suppress=False)
        _keyboard.wait()   # blocks the thread until unregister_all() is called

    _registered.append(hotkey)
    thread = threading.Thread(target=_listen, daemon=True, name="hotkey-listener")
    thread.start()


def unregister_all() -> None:
    """Clean up all listeners. Call on app quit."""
    try:
        _keyboard.unhook_all_hotkeys()
    except Exception:
        pass
    _registered.clear()
