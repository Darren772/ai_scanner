"""
System tray icon using `pystray`.
Icon: assets/icon.png (64x64 PNG)

Menu items:
  renScan            (disabled label)
  ─────────────────
  Show / Hide        -> calls on_toggle()   [default — fires on left-click]
  ─────────────────
  Open Settings      -> calls on_settings()
  View History       -> calls on_history()
  ─────────────────
  Quit               -> calls on_quit()

Runs in a background daemon thread so it doesn't block the main loop.
"""

import os
import threading

import pystray
from PIL import Image, ImageDraw


def _make_fallback_icon() -> Image.Image:
    """Generate a simple icon if icon.png is missing."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill="#1A56DB")
    draw.text((14, 18), "rS", fill="white")
    return img


def start(on_settings, on_history, on_quit, on_toggle) -> pystray.Icon:
    """
    Start tray icon. Runs in daemon thread. Returns the pystray.Icon instance.

    on_toggle   — called on left-click (show/hide main window)
    on_settings — called from menu
    on_history  — called from menu
    on_quit     — called from menu
    """
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    icon_path  = os.path.join(assets_dir, "icon.png")
    image      = Image.open(icon_path) if os.path.exists(icon_path) else _make_fallback_icon()

    menu = pystray.Menu(
        pystray.MenuItem("renScan", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Show / Hide",
            lambda icon, item: on_toggle(),
            default=True,          # fires on left-click on Windows
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Settings", lambda icon, item: on_settings()),
        pystray.MenuItem("View History",  lambda icon, item: on_history()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit",          lambda icon, item: on_quit()),
    )

    icon   = pystray.Icon("renscan", image, "renScan", menu)
    thread = threading.Thread(target=icon.run, daemon=True, name="tray-thread")
    thread.start()
    return icon
