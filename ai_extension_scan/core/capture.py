"""
Screen region capture using `mss`.

Flow:
  1. Receive (x, y, width, height) from the overlay selection
  2. Capture that region across any monitor
  3. Save as a temp PNG via tempfile
  4. Return the temp file path
  5. Optionally delete after use (privacy_mode)
"""

import os
import tempfile

import mss
import mss.tools


def capture_region(x: int, y: int, width: int, height: int) -> str:
    """Capture screen region. Returns path to temp PNG file."""
    monitor = {"top": y, "left": x, "width": width, "height": height}

    with mss.mss() as sct:
        screenshot = sct.grab(monitor)
        fd, path = tempfile.mkstemp(prefix="renscan_", suffix=".png")
        os.close(fd)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=path)

    return path


def delete_temp(path: str) -> None:
    """Delete the temp file. Called after API response if privacy_mode is on."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
