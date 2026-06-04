"""
Fullscreen transparent selection overlay (raw tkinter — NOT CustomTkinter).

Using raw tkinter here because we need pixel-perfect transparency and a
Canvas for rubber-band drawing, which CTk does not support directly.

Behaviour:
  - Fullscreen, always-on-top, semi-transparent dark background
  - Cursor changes to crosshair
  - Click + drag draws a rubber-band rectangle (blue border, stippled fill)
  - Live dimension label shown near the bottom-right of the selection
  - Mouse release -> fires on_select(x, y, width, height) callback
  - Esc or right-click cancels with no side effects

Uses a Toplevel (not Tk) so it shares the existing CTk main-loop and avoids
the "multiple Tk instances" crash that broke repeated scans.
"""

import tkinter as tk

# Module-level guard — prevents opening two overlays at once
_active = False


def show(on_select, on_cancel=None) -> None:
    """Open overlay. Calls on_select(x, y, w, h) on mouse release."""
    global _active
    if _active:
        return
    _active = True

    # Toplevel instead of Tk — the CTk root is the real Tk instance
    root = tk.Toplevel()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.35)
    root.attributes("-topmost", True)
    root.overrideredirect(True)
    root.config(bg="black", cursor="crosshair")

    canvas = tk.Canvas(root, bg="black", highlightthickness=0, cursor="crosshair")
    canvas.pack(fill="both", expand=True)

    state = {
        "start_x": 0,
        "start_y": 0,
        "rect":    None,
        "label":   None,
        "label_bg": None,
        "cancelled": False,
    }

    def _canvas_x(screen_x: int) -> int:
        return screen_x - root.winfo_rootx()

    def _canvas_y(screen_y: int) -> int:
        return screen_y - root.winfo_rooty()

    def _clear_drawing() -> None:
        for key in ("rect", "label", "label_bg"):
            if state[key]:
                canvas.delete(state[key])
                state[key] = None

    def _close_overlay() -> None:
        """Safely destroy the overlay and release the guard."""
        global _active
        try:
            root.destroy()
        except Exception:
            pass
        _active = False

    def on_press(event: tk.Event) -> None:
        state["start_x"] = event.x_root
        state["start_y"] = event.y_root
        _clear_drawing()

    def on_drag(event: tk.Event) -> None:
        x1 = _canvas_x(state["start_x"])
        y1 = _canvas_y(state["start_y"])
        x2 = _canvas_x(event.x_root)
        y2 = _canvas_y(event.y_root)

        _clear_drawing()

        # Rubber-band selection rectangle
        state["rect"] = canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#1A56DB", width=2,
            fill="#1A56DB", stipple="gray25",
        )

        # Dimension label with background pill
        w = abs(event.x_root - state["start_x"])
        h = abs(event.y_root - state["start_y"])
        lx = max(x1, x2) + 8
        ly = max(y1, y2) + 6
        label_text = f"  {w} × {h}  "

        state["label_bg"] = canvas.create_rectangle(
            lx, ly, lx + len(label_text) * 7 + 4, ly + 20,
            fill="#1A56DB", outline="", width=0,
        )
        state["label"] = canvas.create_text(
            lx + 4, ly + 10,
            text=f"{w} × {h}",
            fill="white", anchor="w",
            font=("Segoe UI", 10, "bold"),
        )

    def on_release(event: tk.Event) -> None:
        if state["cancelled"]:
            return

        x = min(state["start_x"], event.x_root)
        y = min(state["start_y"], event.y_root)
        w = abs(event.x_root - state["start_x"])
        h = abs(event.y_root - state["start_y"])

        _close_overlay()

        if w > 5 and h > 5:
            on_select(x, y, w, h)
        elif on_cancel:
            # Selection too small — treat as a cancel so _scanning resets
            on_cancel()

    def on_cancel_event(event: tk.Event) -> None:
        state["cancelled"] = True
        _close_overlay()
        if on_cancel:
            on_cancel()

    canvas.bind("<ButtonPress-1>",   on_press)
    canvas.bind("<B1-Motion>",       on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<ButtonPress-3>",   on_cancel_event)   # right-click cancels
    root.bind("<Escape>",            on_cancel_event)

    # Focus the overlay so keyboard events (Esc) work immediately
    root.focus_force()
