"""
Floating always-on-top results window (CustomTkinter, frameless).

Layout v2:
  - Draggable header with 'renScan', active preset name, minimize and close buttons
  - Summary bar: "⚠ 3 grammar · 1 spelling issue(s) found"
  - Single scrollable report:
      - Color-coded section cards (Grammar 🔴, Spelling 🟡, Structure 🔵, Tone 🟣)
      - Sections with zero issues are hidden automatically
      - Each issue card has a colored left-border strip, readable text, Copy button
      - ✅ All Clear card if no issues found
      - Rewrite section: premium green card at the bottom
  - Loading screen with rotating status messages
  - Footer: "Copy Full Report" + "Copy Rewrite" full-width buttons
  - Esc to dismiss

Multiple panels:
  Each scan creates its own independent ResultsPanel instance.
  Panels are cascade-offset so they are visually distinct on screen.
  Use the minimize button (–) to tuck a panel out of the way without closing it.
"""

import customtkinter as ctk
from utils import clipboard


# ── Design tokens ────────────────────────────────────────────────────────────
_HEADER_BG   = "#1A56DB"
_GRAMMAR_COL = "#e53e3e"
_SPELL_COL   = "#d97706"
_STRUCT_COL  = "#2563eb"
_TONE_COL    = "#7c3aed"
_REWRITE_COL = "#059669"

_SECTION_CFG = [
    ("grammar",   "Grammar",   _GRAMMAR_COL, "🔴"),
    ("spelling",  "Spelling",  _SPELL_COL,   "🟡"),
    ("structure", "Structure", _STRUCT_COL,  "🔵"),
    ("tone",      "Tone",      _TONE_COL,    "🟣"),
]

_LOADING_MSGS = [
    "🔍  Reading your text…",
    "✏️  Checking grammar…",
    "📝  Analysing tone…",
    "🔎  Reviewing structure…",
    "✨  Preparing your report…",
]

# Cascade step — each new panel is offset by this many pixels right+down
_CASCADE_STEP = 32


# ── Panel Window ─────────────────────────────────────────────────────────────

class ResultsPanel(ctk.CTkToplevel):
    """
    Floating results panel window.
    Each scan creates its own independent instance.
    Panels are automatically cascade-positioned so they don't overlap exactly.
    """

    WIDTH  = 530
    HEIGHT = 660

    # Class-level counter drives cascade offset
    _open_count: int = 0

    def __init__(self) -> None:
        super().__init__()
        self.title("renScan")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(True, True)
        self.minsize(430, 500)
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self._result       = None
        self._drag_ox      = 0
        self._drag_oy      = 0
        self._dragged      = False
        self._msg_index    = 0
        self._rotate_id    = None
        self._minimized    = False

        # Capture cascade index before incrementing
        self._cascade_idx = ResultsPanel._open_count
        ResultsPanel._open_count += 1
        self.scan_number = self._cascade_idx + 1

        self._build_ui()
        self._center_cascaded()
        self.bind("<Escape>", lambda _e: self.close())

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Header bar ──
        self._header = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color=_HEADER_BG)
        self._header.pack(fill="x")
        self._header.pack_propagate(False)

        self._header_lbl = ctk.CTkLabel(
            self._header, text=f"  ⬤  renScan #{self.scan_number}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
        )
        self._header_lbl.pack(side="left", padx=10)

        self._preset_lbl = ctk.CTkLabel(
            self._header, text="",
            font=ctk.CTkFont(size=11),
            text_color="#a0c4ff",
        )
        self._preset_lbl.pack(side="left", padx=(0, 6))

        # Close button
        ctk.CTkButton(
            self._header, text="✕", width=36, height=32,
            fg_color="transparent", text_color="white",
            hover_color="#c0392b", corner_radius=6,
            command=self.close,
        ).pack(side="right", padx=8, pady=10)

        # Minimize button
        ctk.CTkButton(
            self._header, text="–", width=36, height=32,
            fg_color="transparent", text_color="white",
            hover_color="#2563eb", corner_radius=6,
            command=self._toggle_minimize,
        ).pack(side="right", padx=(0, 0), pady=10)

        self._header.bind("<ButtonPress-1>", self._drag_start)
        self._header.bind("<B1-Motion>",     self._drag_move)
        for child in self._header.winfo_children():
            child.bind("<ButtonPress-1>", self._drag_start)
            child.bind("<B1-Motion>",     self._drag_move)

        # Accent line under header
        self._header_accent = ctk.CTkFrame(self, height=2, corner_radius=0, fg_color="#4f83ff")
        self._header_accent.pack(fill="x")

        # ── Body ──
        self._body = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray93", "#13141f"))
        self._body.pack(fill="both", expand=True)

        # Loading frame
        self._loading_frame = ctk.CTkFrame(self._body, fg_color="transparent")
        self._loading_frame.place(relx=0.5, rely=0.42, anchor="center")

        self._loading_lbl = ctk.CTkLabel(
            self._loading_frame,
            text=_LOADING_MSGS[0],
            font=ctk.CTkFont(size=15),
        )
        self._loading_lbl.pack(pady=(0, 16))

        self._progress = ctk.CTkProgressBar(
            self._loading_frame, width=250, height=6, mode="indeterminate",
        )
        self._progress.pack()
        self._progress.start()

        ctk.CTkLabel(
            self._loading_frame,
            text="This usually takes a few seconds…",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray55"),
        ).pack(pady=(12, 0))

        # Results area (hidden until ready)
        self._scroll = ctk.CTkScrollableFrame(self._body, fg_color="transparent", corner_radius=0)

        # Footer (hidden until ready)
        self._footer = ctk.CTkFrame(
            self._body, height=62, corner_radius=0,
            fg_color=("white", "#0c0d14"),
        )

        btn_row = ctk.CTkFrame(self._footer, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=12)

        self._btn_report = ctk.CTkButton(
            btn_row, text="📋  Copy Full Report",
            height=38, corner_radius=8,
            fg_color=_HEADER_BG, hover_color="#1647b8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._copy_all,
        )
        self._btn_report.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self._btn_rewrite = ctk.CTkButton(
            btn_row, text="✍  Copy Rewritten Text",
            height=38, corner_radius=8,
            fg_color=_REWRITE_COL, hover_color="#047857",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._copy_rewrite,
        )
        self._btn_rewrite.pack(side="left", fill="x", expand=True)

    # ── Minimize ─────────────────────────────────────────────────────────────

    def _toggle_minimize(self) -> None:
        """Collapse to a tiny square showing the scan number, or restore full size."""
        if self._minimized:
            # Restore
            self._mini_frame.pack_forget()
            
            self._header.pack(fill="x")
            self._header_accent.pack(fill="x")
            self._body.pack(fill="both", expand=True)
            
            self.resizable(True, True)
            self.minsize(430, 500)
            self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
            self._minimized = False
        else:
            # Collapse
            self._header.pack_forget()
            self._header_accent.pack_forget()
            self._body.pack_forget()
            
            if not hasattr(self, "_mini_frame"):
                self._mini_frame = ctk.CTkFrame(
                    self, corner_radius=12,
                    fg_color=_HEADER_BG,
                    border_color="#4f83ff",
                    border_width=2,
                )
                self._mini_lbl = ctk.CTkLabel(
                    self._mini_frame,
                    text=str(self.scan_number),
                    font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="white",
                )
                self._mini_lbl.pack(fill="both", expand=True)
                
                # Bind dragging and clicking
                for widget in (self._mini_frame, self._mini_lbl):
                    widget.bind("<ButtonPress-1>", self._drag_start)
                    widget.bind("<B1-Motion>",     self._drag_move)
                    widget.bind("<ButtonRelease-1>", self._on_mini_click)

            self._mini_frame.pack(fill="both", expand=True)
            self.resizable(False, False)
            self.minsize(0, 0)
            self.geometry("52x52")
            self._minimized = True

    # ── Dragging ─────────────────────────────────────────────────────────────

    def _drag_start(self, event: object) -> None:
        self._drag_ox = event.x_root - self.winfo_x()
        self._drag_oy = event.y_root - self.winfo_y()
        self._dragged = False

    def _drag_move(self, event: object) -> None:
        self._dragged = True
        self.geometry(f"+{event.x_root - self._drag_ox}+{event.y_root - self._drag_oy}")

    def _on_mini_click(self, event: object) -> None:
        if not self._dragged:
            self._toggle_minimize()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _center_cascaded(self) -> None:
        """Center the first panel; subsequent panels are offset by cascade step."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        base_x = (sw - self.WIDTH)  // 2
        base_y = (sh - self.HEIGHT) // 2
        offset = self._cascade_idx * _CASCADE_STEP
        x = base_x + offset
        y = base_y + offset
        self.geometry(f"+{x}+{y}")

    def _rotate_msg(self) -> None:
        self._msg_index = (self._msg_index + 1) % len(_LOADING_MSGS)
        try:
            self._loading_lbl.configure(text=_LOADING_MSGS[self._msg_index])
            self._rotate_id = self.after(2200, self._rotate_msg)
        except Exception:
            pass

    def _build_summary(self, result) -> None:
        """Build the colored summary bar at the top of the scroll area."""
        total = sum(len(getattr(result, k, [])) for k, *_ in _SECTION_CFG)

        bar = ctk.CTkFrame(
            self._scroll, corner_radius=10,
            fg_color=("#dbeafe", "#1e2a4a"),
        )
        bar.pack(fill="x", padx=16, pady=(14, 6))

        if total == 0:
            icon, msg = "✅", "No issues found — your text looks great!"
            color = (_REWRITE_COL, "#5adf90")
        else:
            parts = []
            for key, label, *_ in _SECTION_CFG:
                n = len(getattr(result, key, []))
                if n:
                    parts.append(f"{n} {label.lower()}")
            icon, msg = "⚠", "  ·  ".join(parts) + " issue(s) found"
            color = (_HEADER_BG, "#7aaeff")

        ctk.CTkLabel(
            bar,
            text=f"{icon}  {msg}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=color,
            anchor="w",
        ).pack(padx=14, pady=10, anchor="w")

    def _build_section(self, label: str, color: str, emoji: str, items: list[str]) -> None:
        """Build one color-coded issue section."""
        # Section header row
        hdr = ctk.CTkFrame(self._scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            hdr,
            text=f"{emoji}  {label}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=(color, color),
        ).pack(side="left")

        # Count pill
        pill = ctk.CTkLabel(
            hdr,
            text=f"  {len(items)}  ",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=(color, color),
            text_color="white",
            corner_radius=10,
        )
        pill.pack(side="left", padx=(8, 0))

        # Issue cards
        for item in items:
            # Outer card provides the colored left-strip effect
            outer = ctk.CTkFrame(self._scroll, corner_radius=9, fg_color=(color, color))
            outer.pack(fill="x", padx=16, pady=3)

            # Inner white/dark card sits 4px from the left, covering the rest
            inner = ctk.CTkFrame(outer, corner_radius=7, fg_color=("white", "#1c1e2e"))
            inner.pack(fill="both", expand=True, padx=(4, 0), pady=0)

            ctk.CTkLabel(
                inner,
                text=item,
                wraplength=370,
                justify="left",
                anchor="w",
                font=ctk.CTkFont(size=14),
                text_color=("gray10", "gray90"),
            ).pack(side="left", padx=12, pady=10, fill="x", expand=True)

            ctk.CTkButton(
                inner,
                text="Copy",
                width=56, height=28, corner_radius=6,
                fg_color=("gray90", "#2a2d3e"),
                text_color=(color, color),
                hover_color=("gray82", "#363a52"),
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda t=item: clipboard.copy(t),
            ).pack(side="right", padx=10, pady=8)

    def _build_rewrite(self, text: str) -> None:
        """Build the premium Rewrite card at the bottom."""
        # Divider
        ctk.CTkFrame(self._scroll, height=1, fg_color=("gray80", "gray25")).pack(
            fill="x", padx=16, pady=(18, 0)
        )

        hdr = ctk.CTkFrame(self._scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            hdr,
            text="✍  Suggested Rewrite",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=(_REWRITE_COL, "#34d399"),
        ).pack(side="left")

        # The rewrite card — green-tinted background
        card = ctk.CTkFrame(
            self._scroll, corner_radius=10,
            fg_color=("#ecfdf5", "#0d1f17"),
            border_color=(_REWRITE_COL, "#1a5c3a"),
            border_width=1,
        )
        card.pack(fill="x", padx=16, pady=(0, 20))

        ctk.CTkLabel(
            card,
            text=text,
            wraplength=440,
            justify="left",
            anchor="nw",
            font=ctk.CTkFont(size=14),
            text_color=("gray10", "gray92"),
        ).pack(padx=16, pady=14, fill="x", anchor="nw")

    def _build_all_clear(self) -> None:
        """Show a friendly 'All Clear' card when there are zero issues."""
        card = ctk.CTkFrame(
            self._scroll, corner_radius=12,
            fg_color=("#ecfdf5", "#0d1f17"),
            border_color=(_REWRITE_COL, "#1a5c3a"),
            border_width=1,
        )
        card.pack(fill="x", padx=16, pady=(6, 4))

        ctk.CTkLabel(
            card,
            text="🎉  Great writing!\nNo grammar, spelling, structure or tone issues were found.",
            font=ctk.CTkFont(size=14),
            text_color=(_REWRITE_COL, "#34d399"),
            justify="center",
        ).pack(pady=22, padx=20)

    # ── Public API ────────────────────────────────────────────────────────────

    def show_loading(self) -> None:
        self._scroll.pack_forget()
        self._footer.pack_forget()
        self._msg_index = 0
        self._loading_lbl.configure(text=_LOADING_MSGS[0])
        self._loading_frame.place(relx=0.5, rely=0.42, anchor="center")
        self._progress.start()
        self._rotate_id = self.after(2200, self._rotate_msg)

    def show(self, result) -> None:
        self._result = result

        # Stop loading animation
        if self._rotate_id:
            try:
                self.after_cancel(self._rotate_id)
            except Exception:
                pass
            self._rotate_id = None
        self._progress.stop()
        self._loading_frame.place_forget()

        # Clear any previous results
        for w in self._scroll.winfo_children():
            w.destroy()

        # Update preset name in header
        try:
            from config import settings as _s, presets as _p
            _pid  = _s.load().get("active_preset", "general")
            _name = _p.load_presets().get(_pid, {}).get("name", "").replace("✏ ", "")
            self._preset_lbl.configure(text=f"· {_name}" if _name else "")
        except Exception:
            pass

        # Summary bar
        self._build_summary(result)

        # Issue sections — only render non-empty ones
        has_issues = False
        for key, label, color, emoji in _SECTION_CFG:
            items = getattr(result, key, [])
            if items:
                has_issues = True
                self._build_section(label, color, emoji, items)

        if not has_issues:
            self._build_all_clear()

        # Rewrite
        if result.rewrite:
            self._build_rewrite(result.rewrite)

        # If panel was minimized while loading, restore it now that results are ready
        if self._minimized:
            self._toggle_minimize()

        self._scroll.pack(fill="both", expand=True)
        self._footer.pack(fill="x", side="bottom")

    def show_error(self, error_msg: str) -> None:
        """Display an error message inside the panel instead of silently closing it."""
        # Stop loading animation
        if self._rotate_id:
            try:
                self.after_cancel(self._rotate_id)
            except Exception:
                pass
            self._rotate_id = None
        self._progress.stop()
        self._loading_frame.place_forget()

        # Clear any previous results
        for w in self._scroll.winfo_children():
            w.destroy()

        # Error Card (red-tinted background)
        card = ctk.CTkFrame(
            self._scroll, corner_radius=12,
            fg_color=("#fdecea", "#2a1616"),
            border_color=(_GRAMMAR_COL, "#5c1a1a"),
            border_width=1,
        )
        card.pack(fill="x", padx=16, pady=20)

        ctk.CTkLabel(
            card,
            text=f"❌  Scan Failed\n\n{error_msg}",
            font=ctk.CTkFont(size=14),
            text_color=(_GRAMMAR_COL, "#e74c3c"),
            justify="center",
            wraplength=400,
        ).pack(pady=22, padx=20)

        # Restore window size if minimized
        if self._minimized:
            self._toggle_minimize()

        self._scroll.pack(fill="both", expand=True)
        self._footer.pack_forget()

    def _copy_all(self) -> None:
        if not self._result:
            return
        lines = []
        for label, items in [
            ("GRAMMAR",   self._result.grammar),
            ("SPELLING",  self._result.spelling),
            ("STRUCTURE", self._result.structure),
            ("TONE",      self._result.tone),
        ]:
            if items:
                lines.append(f"## {label}")
                lines.extend(f"- {i}" for i in items)
        if self._result.rewrite:
            lines.append("\n## REWRITE")
            lines.append(self._result.rewrite)
        clipboard.copy("\n".join(lines))

    def _copy_rewrite(self) -> None:
        if self._result and self._result.rewrite:
            clipboard.copy(self._result.rewrite)

    def close(self) -> None:
        try:
            if self._rotate_id:
                self.after_cancel(self._rotate_id)
            self._progress.stop()
            # Decrement open count so future panels don't cascade infinitely
            ResultsPanel._open_count = max(0, ResultsPanel._open_count - 1)
            self.destroy()
        except Exception:
            pass


# ── Backward-compat module-level helpers ─────────────────────────────────────
# These are kept so any code that still calls results_panel.show() or
# results_panel.show_loading() continues to work unchanged.

_panel: ResultsPanel | None = None


def _get_or_create() -> ResultsPanel:
    global _panel
    if _panel is None or not _panel.winfo_exists():
        _panel = ResultsPanel()
    return _panel


def show(result) -> None:
    _get_or_create().show(result)


def show_loading() -> None:
    _get_or_create().show_loading()


def close() -> None:
    global _panel
    if _panel and _panel.winfo_exists():
        _panel.close()
    _panel = None




