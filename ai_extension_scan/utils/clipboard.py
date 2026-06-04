"""
Cross-platform clipboard write using tkinter's clipboard interface.
"""

import tkinter as tk


def copy(text: str) -> None:
    """Copy text to system clipboard."""
    root = tk.Tk()
    root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()          # flush so clipboard persists after window closes
    root.after(300, root.destroy)
    root.mainloop()
