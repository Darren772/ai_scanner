"""
Main dashboard window for renScan.

Layout:
  ┌──────────────┬──────────────────────────────┐
  │   Sidebar    │        Content Area          │
  │              │                              │
  │  🏠 Home     │  Home / History / Settings   │
  │  📋 History  │  panel (switches on nav)     │
  │  ⚙ Settings │                              │
  │  ─────────── │                              │
  │  ▶ Scan Now  │                              │
  └──────────────┴──────────────────────────────┘

Behaviour:
  - Window opens on app launch
  - X button hides to tray (does NOT quit)
  - show() / hide() / toggle() control visibility
  - navigate(tab) switches to "home" | "history" | "settings"
  - refresh_home() re-populates home stats (call after each scan)
"""

import threading
import customtkinter as ctk

from api.client import load_provider_config, save_provider_config, PROVIDER_DISPLAY_NAMES, PROVIDER_DEFAULT_MODELS
from config import settings as settings_module
from history import log as history_log
from utils import autostart, clipboard


# ── Colour constants ────────────────────────────────────────────────────────
_SIDEBAR_BG   = ("#1e2a3a", "#0f1923")
_SIDEBAR_HOVER = ("#2a3a4e", "#1a2535")
_ACTIVE_BG    = ("#243447", "#1c2d40")
_ACCENT       = "#1A56DB"
_ACCENT_HOVER = "#1647b8"


class MainWindow:
    """Main application dashboard window."""

    def __init__(self, root: ctk.CTk, on_scan) -> None:
        self._root    = root
        self._on_scan = on_scan
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._home_dirty = True   # True = needs rebuild before next display

        self._configure_root()
        self._build_layout()
        self._show_home()

    # ── Root configuration ──────────────────────────────────────────────────

    def _configure_root(self) -> None:
        self._root.title("renScan")
        self._root.geometry("960x660")
        self._root.minsize(700, 500)
        self._root.protocol("WM_DELETE_WINDOW", self.hide)

        # Grid: sidebar (col 0) | content (col 1)
        self._root.grid_columnconfigure(1, weight=1)
        self._root.grid_rowconfigure(0, weight=1)

    # ── Top-level layout ────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        self._build_sidebar()

        # Content container — all panels stack here
        self._content = ctk.CTkFrame(self._root, corner_radius=0, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Build panels (all placed in same cell, raised on nav)
        self._home_panel     = self._build_home_panel()
        self._history_panel  = self._build_history_panel()
        self._settings_panel = self._build_settings_panel()

        for panel in (self._home_panel, self._history_panel, self._settings_panel):
            panel.grid(row=0, column=0, sticky="nsew")

    # ── Sidebar ─────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        sb = ctk.CTkFrame(self._root, width=210, corner_radius=0, fg_color=_SIDEBAR_BG)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(5, weight=1)   # spacer pushes scan btn to bottom

        # ── Logo ──
        logo_frame = ctk.CTkFrame(sb, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 20), sticky="w")

        ctk.CTkLabel(
            logo_frame, text="renScan",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="AI Proofreader",
            font=ctk.CTkFont(size=11),
            text_color="#8899aa",
        ).pack(anchor="w")

        # ── Nav items ──
        _nav_items = [
            ("home",     "🏠  Home",     self._show_home),
            ("history",  "📋  History",  self._show_history),
            ("settings", "⚙  Settings", self._show_settings),
        ]

        for row, (key, label, cmd) in enumerate(_nav_items, start=1):
            btn = ctk.CTkButton(
                sb, text=label,
                anchor="w",
                width=178, height=42,
                corner_radius=8,
                fg_color="transparent",
                hover_color=_SIDEBAR_HOVER,
                text_color="white",
                font=ctk.CTkFont(size=13),
                command=cmd,
            )
            btn.grid(row=row, column=0, padx=16, pady=3, sticky="ew")
            self._nav_btns[key] = btn

        # ── Spacer (row 5 expands) ──

        # ── Divider ──
        ctk.CTkFrame(sb, height=1, fg_color="#2a3a4e").grid(
            row=6, column=0, sticky="ew", padx=16, pady=(0, 10)
        )

        # ── Scan Now button ──
        ctk.CTkButton(
            sb,
            text="▶   Scan Now",
            width=178, height=44,
            corner_radius=10,
            fg_color=_ACCENT,
            hover_color=_ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._trigger_scan,
        ).grid(row=7, column=0, padx=16, pady=(0, 8), sticky="ew")

        # ── Version label ──
        ctk.CTkLabel(
            sb, text="v1.0",
            font=ctk.CTkFont(size=10),
            text_color="#445566",
        ).grid(row=8, column=0, pady=(2, 16))

    def _set_nav_active(self, key: str) -> None:
        for k, btn in self._nav_btns.items():
            btn.configure(fg_color=_ACTIVE_BG if k == key else "transparent")

    def _trigger_scan(self) -> None:
        """Close/hide window then trigger overlay so user can see the screen."""
        self.hide()
        self._root.after(200, self._on_scan)

    # ── Home Panel ──────────────────────────────────────────────────────────

    def _build_home_panel(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._content, corner_radius=0, fg_color="transparent")
        return frame

    def refresh_home(self) -> None:
        """Mark home as dirty so it rebuilds on next visit (or rebuild now if visible)."""
        self._home_dirty = True
        # If home is already the front panel, refresh immediately
        try:
            if self._home_panel.winfo_ismapped():
                self._populate_home(self._home_panel)
                self._home_dirty = False
        except Exception:
            pass

    def _populate_home(self, frame: ctk.CTkFrame) -> None:
        for w in frame.winfo_children():
            w.destroy()

        from datetime import datetime
        entries   = history_log.load_all()
        today_str = datetime.now().date().isoformat()
        today_n   = sum(1 for e in entries if e["timestamp"][:10] == today_str)

        # Scrollable so content never gets clipped on small windows
        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # ── Greeting ──
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")

        ctk.CTkLabel(
            scroll, text=f"{greeting} 👋",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(anchor="w", padx=30, pady=(28, 2))

        ctk.CTkLabel(
            scroll,
            text="Your AI writing assistant is ready.",
            font=ctk.CTkFont(size=13),
            text_color=("gray45", "gray60"),
        ).pack(anchor="w", padx=30, pady=(0, 20))

        # ── Provider badge ──
        cfg          = load_provider_config()
        provider_id  = cfg.get("provider", "gemini")
        provider_lbl = PROVIDER_DISPLAY_NAMES.get(provider_id, provider_id.title())
        model        = cfg.get("model", "—")

        badge = ctk.CTkFrame(scroll, fg_color=(_ACCENT, "#1a2d5a"), corner_radius=10)
        badge.pack(fill="x", padx=30, pady=(0, 18))
        ctk.CTkLabel(
            badge,
            text=f"  🤖  {provider_lbl}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
            anchor="w",
        ).pack(side="left", padx=10, pady=11)
        ctk.CTkLabel(
            badge,
            text=f"{model}  ",
            font=ctk.CTkFont(size=12),
            text_color="#a0c4ff",
            anchor="e",
        ).pack(side="right", padx=10, pady=11)

        # ── Stats row ──
        stats_row = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_row.pack(fill="x", padx=30, pady=(0, 18))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)

        for col, (value, label, color) in enumerate([
            (str(len(entries)), "Total Checks",  (_ACCENT, "#3a7bd5")),
            (str(today_n),      "Today",          ("#059669", "#34d399")),
        ]):
            card = ctk.CTkFrame(stats_row, corner_radius=14, fg_color=("white", "#1a1c2e"))
            card.grid(row=0, column=col, padx=(0, 12) if col == 0 else 0, sticky="ew")
            ctk.CTkLabel(
                card, text=value,
                font=ctk.CTkFont(size=36, weight="bold"),
                text_color=color,
            ).pack(pady=(16, 2))
            ctk.CTkLabel(
                card, text=label,
                font=ctk.CTkFont(size=11),
                text_color=("gray50", "gray60"),
            ).pack(pady=(0, 16))

        # ── Hotkey display ──
        settings = settings_module.load()
        hk_text  = settings.get("hotkey", "ctrl+shift+s").upper()

        hk_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("white", "#1a1c2e"))
        hk_card.pack(fill="x", padx=30, pady=(0, 12))

        ctk.CTkLabel(
            hk_card, text="⌨  Global Hotkey",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(side="left", padx=18, pady=14)

        ctk.CTkLabel(
            hk_card,
            text=f"  {hk_text}  ",
            font=ctk.CTkFont(size=12),
            fg_color=("#dbeafe", "#1e2d4a"),
            corner_radius=6,
            text_color=(_ACCENT, "#7aaeff"),
        ).pack(side="right", padx=18, pady=14, ipadx=6, ipady=4)

        # ── Active preset selector ──
        from config import presets
        all_presets = presets.load_presets()
        active_preset_id = settings.get("active_preset", "general")

        preset_options = []
        name_to_id = {}
        for pid, pdata in all_presets.items():
            disp = pdata["name"]
            preset_options.append(disp)
            name_to_id[disp] = pid

        current_disp = all_presets.get(active_preset_id, all_presets.get("general", {}))["name"]

        ctx_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("white", "#1a1c2e"))
        ctx_card.pack(fill="x", padx=30, pady=(0, 12))

        ctk.CTkLabel(
            ctx_card, text="🎯  Writing Preset",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(side="left", padx=18, pady=14)

        def _on_preset_change(val: str) -> None:
            selected_id = name_to_id.get(val, "general")
            current_settings = settings_module.load()
            current_settings["active_preset"] = selected_id
            settings_module.save(current_settings)

        preset_dropdown = ctk.CTkOptionMenu(
            ctx_card,
            values=preset_options,
            command=_on_preset_change,
            width=200,
        )
        preset_dropdown.set(current_disp)
        preset_dropdown.pack(side="right", padx=18, pady=14)

        # ── Last scan summary ──
        if entries:
            last = entries[0]
            ts   = last["timestamp"][:16].replace("T", " ")
            mode = last["mode"].upper()
            r    = last["result"]
            n_issues = sum(len(r.get(k, [])) for k in ("grammar", "spelling", "structure", "tone"))
            if n_issues > 0:
                badge_bg   = ("#fee2e2", "#7f1d1d")
                badge_text = ("#dc2626", "#f87171")
                issue_txt  = f"{n_issues} issue{'s' if n_issues != 1 else ''} found"
            else:
                badge_bg   = ("#d1fae5", "#064e3b")
                badge_text = ("#059669", "#34d399")
                issue_txt  = "✅ No issues found"

            last_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("white", "#1a1c2e"))
            last_card.pack(fill="x", padx=30, pady=(0, 20))

            ctk.CTkLabel(
                last_card, text="🕐  Last Scan",
                font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            ).pack(anchor="w", padx=18, pady=(14, 4))

            detail_row = ctk.CTkFrame(last_card, fg_color="transparent")
            detail_row.pack(fill="x", padx=18, pady=(0, 14))

            ctk.CTkLabel(
                detail_row,
                text=f"{ts}  ·  {mode}",
                font=ctk.CTkFont(size=12),
                text_color=("gray50", "gray60"),
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                detail_row,
                text=f"  {issue_txt}  ",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=badge_bg,
                text_color=badge_text,
                corner_radius=8,
            ).pack(side="right")


            ctk.CTkButton(
                last_card, text="View in History →",
                width=160, height=30,
                fg_color="transparent", border_width=1,
                hover_color=("gray90", "gray25"),
                command=self._show_history,
            ).pack(anchor="e", padx=18, pady=(0, 14))
        else:
            # ── How to use hint card for first-time users ──
            empty_card = ctk.CTkFrame(scroll, corner_radius=14, fg_color=("white", "#1a1c2e"))
            empty_card.pack(fill="x", padx=30, pady=(0, 20))
            
            ctk.CTkLabel(
                empty_card, text="💡  How to Use renScan",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            ).pack(anchor="w", padx=20, pady=(16, 8))
            
            steps = [
                "1. Press the global hotkey (or click 'Scan Now' in the sidebar).",
                "2. Click and drag a selection box over the text on your screen.",
                "3. Review the color-coded issues and suggested rewrite instantly!"
            ]
            for step in steps:
                ctk.CTkLabel(
                    empty_card, text=step,
                    font=ctk.CTkFont(size=12),
                    text_color=("gray35", "gray70"),
                    justify="left", anchor="w",
                ).pack(anchor="w", padx=20, pady=3)
                
            # Add a small buffer at the bottom
            ctk.CTkLabel(empty_card, text="", height=4).pack()

    def _show_home(self) -> None:
        self._set_nav_active("home")
        if self._home_dirty:
            self._populate_home(self._home_panel)
            self._home_dirty = False
        self._home_panel.tkraise()

    # ── History Panel ───────────────────────────────────────────────────────

    def _build_history_panel(self) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(self._content, corner_radius=0, fg_color="transparent")

        # ── Header ──
        hdr = ctk.CTkFrame(outer, fg_color="transparent")
        hdr.pack(fill="x", padx=30, pady=(24, 12))
        ctk.CTkLabel(hdr, text="History", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        clear_btn = ctk.CTkButton(
            hdr, text="Clear All", width=100,
            fg_color="#c0392b", hover_color="#922b21",
        )
        clear_btn.pack(side="right")

        # ── Two-panel layout ──
        panels = ctk.CTkFrame(outer, fg_color="transparent")
        panels.pack(fill="both", expand=True, padx=30, pady=(0, 16))
        panels.grid_columnconfigure(0, weight=1)
        panels.grid_columnconfigure(1, weight=2)
        panels.grid_rowconfigure(0, weight=1)

        # Left: list
        left = ctk.CTkFrame(panels, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Entries", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=10)

        list_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        list_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        # Right: detail
        right = ctk.CTkFrame(panels, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        right_hdr = ctk.CTkFrame(right, fg_color="transparent")
        right_hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 0))

        detail_title = ctk.CTkLabel(right_hdr, text="Select an entry →", font=ctk.CTkFont(weight="bold"))
        detail_title.pack(side="left")

        copy_rw_btn = ctk.CTkButton(
            right_hdr, text="Copy Rewrite", width=120, state="disabled",
            fg_color=("gray80", "gray30"), text_color=("black", "white"),
            hover_color=("gray70", "gray40"),
        )
        copy_rw_btn.pack(side="right")

        detail_scroll = ctk.CTkScrollableFrame(right, fg_color="transparent")
        detail_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        # State
        _state: dict = {"rewrite": ""}

        def _show_detail(entry: dict) -> None:
            for w in detail_scroll.winfo_children():
                w.destroy()

            r    = entry["result"]
            ts   = entry["timestamp"][:19].replace("T", " ")
            mode = entry["mode"].upper()
            detail_title.configure(text=f"{ts}  ·  {mode}")

            for sec_label, key in [("Grammar","grammar"),("Spelling","spelling"),("Structure","structure"),("Tone","tone")]:
                items = r.get(key, [])
                if items:
                    ctk.CTkLabel(
                        detail_scroll, text=sec_label,
                        font=ctk.CTkFont(size=12, weight="bold"),
                        text_color=("gray40", "gray70"), anchor="w",
                    ).pack(anchor="w", pady=(10, 2))
                    for item in items:
                        ctk.CTkLabel(
                            detail_scroll, text=f"  • {item}",
                            wraplength=360, justify="left", anchor="w",
                            font=ctk.CTkFont(size=12),
                        ).pack(anchor="w")

            rewrite = r.get("rewrite", "")
            if rewrite:
                ctk.CTkLabel(
                    detail_scroll, text="Rewrite",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=("gray40", "gray70"), anchor="w",
                ).pack(anchor="w", pady=(14, 2))
                ctk.CTkLabel(
                    detail_scroll, text=rewrite,
                    wraplength=360, justify="left", anchor="w",
                    font=ctk.CTkFont(size=12),
                ).pack(anchor="w", pady=(0, 10))

            _state["rewrite"] = rewrite
            copy_rw_btn.configure(
                state="normal" if rewrite else "disabled",
                command=lambda: clipboard.copy(_state["rewrite"]),
            )

        def _refresh() -> None:
            for w in list_scroll.winfo_children():
                w.destroy()

            entries = history_log.load_all()
            if not entries:
                ctk.CTkLabel(
                    list_scroll,
                    text="No history yet.",
                    text_color=("gray50", "gray60"),
                ).pack(pady=30)
                return

            for entry in entries:
                ts      = entry["timestamp"][:16].replace("T", " ")
                mode    = entry["mode"].upper()
                r       = entry["result"]
                preview = (
                    (r.get("grammar") or r.get("spelling") or r.get("structure") or r.get("tone") or [""])[0]
                )[:42] or "(no issues)"

                row = ctk.CTkFrame(list_scroll, corner_radius=8, fg_color=("white", "gray20"))
                row.pack(fill="x", pady=3)

                ctk.CTkButton(
                    row,
                    text=f"{ts}  [{mode}]\n{preview}",
                    anchor="w",
                    fg_color="transparent",
                    hover_color=("gray90", "gray28"),
                    text_color=("black", "white"),
                    font=ctk.CTkFont(size=11),
                    command=lambda e=entry: _show_detail(e),
                ).pack(side="left", fill="x", expand=True, padx=6, pady=6)

                ctk.CTkButton(
                    row, text="🗑", width=30, height=28,
                    fg_color="transparent",
                    hover_color=("#fdecea", "#5c1a1a"),
                    text_color=("#c0392b", "#e74c3c"),
                    command=lambda eid=entry["id"]: [history_log.delete(eid), _refresh()],
                ).pack(side="right", padx=6)

        clear_btn.configure(command=lambda: [history_log.clear(), _refresh()])

        # Store refresh so we can call it when switching to this tab
        self._history_refresh = _refresh

        return outer

    def _show_history(self) -> None:
        self._set_nav_active("history")
        self._history_refresh()
        self._history_panel.tkraise()

    # ── Settings Panel ──────────────────────────────────────────────────────

    def _build_settings_panel(self) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(self._content, corner_radius=0, fg_color="transparent")

        ctk.CTkLabel(
            outer, text="Settings",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=30, pady=(24, 8))

        form = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30, pady=0)

        current      = settings_module.load()
        provider_cfg = load_provider_config()

        def _section(text: str) -> None:
            ctk.CTkLabel(
                form, text=text.upper(),
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=("gray50", "gray60"),
            ).pack(anchor="w", pady=(16, 3))

        # ── AI Provider ──
        _section("AI Provider")

        _pid_list   = list(PROVIDER_DISPLAY_NAMES.keys())
        _plbl_list  = list(PROVIDER_DISPLAY_NAMES.values())

        cur_pid      = provider_cfg.get("provider", "gemini")
        cur_lbl      = PROVIDER_DISPLAY_NAMES.get(cur_pid, "Google Gemini")
        provider_var = ctk.StringVar(value=cur_lbl)

        ctk.CTkOptionMenu(
            form, variable=provider_var, values=_plbl_list, width=230,
            command=lambda lbl: _on_provider_change(lbl),
        ).pack(anchor="w")

        # Model
        model_row = ctk.CTkFrame(form, fg_color="transparent")
        model_row.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(model_row, text="Model:", width=60, anchor="w").pack(side="left")
        model_var = ctk.StringVar(value=provider_cfg.get("model", "gemini-1.5-flash"))
        ctk.CTkEntry(model_row, textvariable=model_var, placeholder_text="Model name").pack(side="left", fill="x", expand=True)

        def _on_provider_change(lbl: str) -> None:
            pid = _pid_list[_plbl_list.index(lbl)]
            model_var.set(PROVIDER_DEFAULT_MODELS.get(pid, ""))
            install_hint.configure(text=_INSTALL_HINTS.get(lbl, ""))

        # API Key
        ctk.CTkLabel(form, text="API Key:", anchor="w", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        key_row = ctk.CTkFrame(form, fg_color="transparent")
        key_row.pack(fill="x")

        key_var   = ctk.StringVar(value=provider_cfg.get("api_key", ""))
        key_entry = ctk.CTkEntry(key_row, textvariable=key_var, show="*", placeholder_text="Paste your API key")
        key_entry.pack(side="left", fill="x", expand=True)

        _show_k = {"on": False}
        def _toggle_key() -> None:
            _show_k["on"] = not _show_k["on"]
            key_entry.configure(show="" if _show_k["on"] else "*")
            tog.configure(text="🙈" if _show_k["on"] else "👁")

        tog = ctk.CTkButton(key_row, text="👁", width=38, height=34,
                            fg_color="transparent", border_width=1, command=_toggle_key)
        tog.pack(side="left", padx=(6, 0))

        _INSTALL_HINTS = {
            "Google Gemini":    "",
            "OpenAI GPT":       "Requires:  pip install openai",
            "Anthropic Claude": "Requires:  pip install anthropic",
        }
        install_hint = ctk.CTkLabel(form, text=_INSTALL_HINTS.get(cur_lbl, ""),
                                    font=ctk.CTkFont(size=10), text_color=("gray50","gray60"), anchor="w")
        install_hint.pack(anchor="w")

        # ── Hotkey ──
        _section("Hotkey")
        hk_row = ctk.CTkFrame(form, fg_color="transparent")
        hk_row.pack(fill="x")

        hotkey_var   = ctk.StringVar(value=current.get("hotkey", "ctrl+shift+s"))
        hotkey_entry = ctk.CTkEntry(hk_row, textvariable=hotkey_var)
        hotkey_entry.pack(side="left", fill="x", expand=True)

        _rec = {"active": False, "keys": [], "hook": None}

        def _start_record() -> None:
            if _rec["active"]:
                return
            import keyboard as _kb
            _rec["active"] = True
            _rec["keys"].clear()
            rec_btn.configure(text="Recording…", fg_color="#c0392b")
            hotkey_entry.configure(state="disabled")

            def _on_key(e) -> None:
                if e.name not in _rec["keys"]:
                    _rec["keys"].append(e.name)

            _rec["hook"] = _kb.on_press(_on_key)

            def _finish() -> None:
                _rec["active"] = False
                if _rec["hook"]:
                    _kb.unhook(_rec["hook"])
                if _rec["keys"]:
                    hotkey_var.set("+".join(dict.fromkeys(_rec["keys"])))
                rec_btn.configure(text="Record", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
                hotkey_entry.configure(state="normal")

            threading.Timer(3.0, lambda: self._root.after(0, _finish)).start()

        rec_btn = ctk.CTkButton(hk_row, text="Record", width=80, command=_start_record)
        rec_btn.pack(side="left", padx=(6, 0))

        # ── Check Mode ──
        _section("Default Check Mode")
        mode_var = ctk.StringVar(value=current.get("check_mode", "full"))
        ctk.CTkOptionMenu(form, variable=mode_var,
                          values=["full","grammar","spelling","structure","tone"], width=200).pack(anchor="w")

        # ── Appearance ──
        _section("Appearance Mode")
        appear_var = ctk.StringVar(value=current.get("appearance_mode", "system").capitalize())
        ctk.CTkSegmentedButton(form, values=["Light","Dark","System"], variable=appear_var).pack(anchor="w")

        # ── Options ──
        _section("Options")
        autostart_var = ctk.BooleanVar(value=current.get("auto_start", False))
        ctk.CTkSwitch(form, text="Auto-start on boot", variable=autostart_var).pack(anchor="w", pady=4)

        history_var = ctk.BooleanVar(value=current.get("save_history", True))
        ctk.CTkSwitch(form, text="Save history (text only, no images)", variable=history_var).pack(anchor="w", pady=4)

        priv = ctk.CTkSwitch(form, text="Privacy mode — auto-delete screenshot  🔒")
        priv.select()
        priv.configure(state="disabled")
        priv.pack(anchor="w", pady=4)

        # Max concurrent scans row
        scans_row = ctk.CTkFrame(form, fg_color="transparent")
        scans_row.pack(anchor="w", pady=4)
        ctk.CTkLabel(scans_row, text="Max concurrent scans:   ", anchor="w").pack(side="left")
        concurrent_var = ctk.StringVar(value=str(current.get("max_concurrent_scans", 3)))
        ctk.CTkOptionMenu(scans_row, variable=concurrent_var, values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], width=80).pack(side="left")

        # ── Writing Contexts ──
        from config import presets as presets_module
        _section("Writing Contexts")

        ctx_list_frame = ctk.CTkScrollableFrame(form, height=180, fg_color=("gray93", "gray18"), corner_radius=8)
        ctx_list_frame.pack(fill="x", pady=(4, 6))

        def _refresh_ctx_list() -> None:
            for w in ctx_list_frame.winfo_children():
                w.destroy()
            all_p = presets_module.load_presets()
            active_id = settings_module.load().get("active_preset", "general")
            for pid, pdata in all_p.items():
                row = ctk.CTkFrame(ctx_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)

                active_indicator = "●  " if pid == active_id else "○  "
                is_active = pid == active_id

                def _make_preview(p_id=pid, p_data=pdata):
                    def _open():
                        pop = ctk.CTkToplevel(self._root)
                        pop.title(f"Preset — {p_data['name']}")
                        pop.geometry("480x320")
                        pop.attributes("-topmost", True)
                        pop.resizable(True, True)
                        pop.transient(self._root)
                        pop.grab_set()

                        ctk.CTkLabel(
                            pop, text=p_data["name"],
                            font=ctk.CTkFont(size=16, weight="bold"),
                        ).pack(anchor="w", padx=20, pady=(18, 4))

                        desc = p_data.get("description", "")
                        if desc:
                            ctk.CTkLabel(
                                pop, text=desc,
                                font=ctk.CTkFont(size=11),
                                text_color=("gray50", "gray60"),
                                anchor="w",
                            ).pack(anchor="w", padx=20, pady=(0, 10))

                        ctk.CTkLabel(
                            pop, text="Rules / Instructions:",
                            font=ctk.CTkFont(size=12, weight="bold"),
                            anchor="w",
                        ).pack(anchor="w", padx=20, pady=(0, 4))

                        rules_box = ctk.CTkTextbox(pop, height=140, wrap="word")
                        rules_box.pack(fill="both", expand=True, padx=20, pady=(0, 14))
                        rules_box.insert("0.0", p_data.get("rules", "(no rules defined)"))
                        rules_box.configure(state="disabled")

                        ctk.CTkButton(pop, text="Close", width=100,
                                      command=pop.destroy).pack(pady=(0, 16))
                    return _open

                name_btn = ctk.CTkButton(
                    row,
                    text=f"{active_indicator}{pdata['name']}",
                    anchor="w",
                    fg_color="transparent",
                    hover_color=("gray88", "gray25"),
                    text_color=(_ACCENT, "#7aaeff") if is_active else ("gray20", "gray80"),
                    font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                    command=_make_preview(),
                )
                name_btn.pack(side="left", padx=8, pady=4)

                ctk.CTkLabel(
                    row,
                    text=pdata.get("description", ""),
                    font=ctk.CTkFont(size=10),
                    text_color=("gray50", "gray60"),
                    anchor="w",
                ).pack(side="left", padx=(0, 8), pady=4)

                if pdata.get("is_custom", False):
                    def _make_delete(p=pid):
                        def _do():
                            presets_module.delete_custom_preset(p)
                            _refresh_ctx_list()
                        return _do
                    ctk.CTkButton(
                        row, text="🗑", width=30, height=24,
                        fg_color="transparent",
                        hover_color=("#fdecea", "#5c1a1a"),
                        text_color=("#c0392b", "#e74c3c"),
                        command=_make_delete(),
                    ).pack(side="right", padx=4)

        _refresh_ctx_list()

        def _open_add_preset_modal() -> None:
            modal = ctk.CTkToplevel(self._root)
            modal.title("Create Custom Preset")
            modal.geometry("500x380")
            modal.attributes("-topmost", True)
            modal.resizable(False, False)
            modal.transient(self._root)
            modal.grab_set()

            ctk.CTkLabel(modal, text="Create Custom Preset", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))

            # Name Input
            name_var = ctk.StringVar()
            ctk.CTkEntry(modal, textvariable=name_var, placeholder_text="Preset name (e.g. Professional Editor)", width=420).pack(pady=(10, 5))

            # Rules Input (Textbox for multiline support)
            rules_textbox = ctk.CTkTextbox(modal, width=420, height=140)
            rules_textbox.pack(pady=5)
            _placeholder = "Context rules for the AI (e.g. You're a professional AI that will check grammar without fixing structure...)"
            rules_textbox.insert("0.0", _placeholder)

            def _clear_placeholder(e):
                if rules_textbox.get("0.0", "end").strip() == _placeholder:
                    rules_textbox.delete("0.0", "end")
            rules_textbox.bind("<FocusIn>", _clear_placeholder)

            def _save_modal_preset() -> None:
                name  = name_var.get().strip()
                rules = rules_textbox.get("0.0", "end").strip()
                if rules == _placeholder:
                    rules = ""
                if not name or not rules:
                    return

                # Disable button and run enhancement in background thread
                save_btn.configure(text="Enhancing with AI…", state="disabled")

                import re, time
                from core.enhancer import enhance_preset

                _name, _rules = name, rules

                def _do_enhance() -> None:
                    """Runs in background thread — no Tkinter calls allowed here."""
                    enhanced = enhance_preset(_rules)
                    pid = re.sub(r"[^a-z0-9_]", "_", _name.lower()) + "_" + str(int(time.time()))[-4:]
                    presets_module.save_custom_preset(pid, f"✏ {_name}", enhanced, "")
                    try:
                        modal.after(0, _finish)
                    except Exception:
                        pass

                def _finish() -> None:
                    _refresh_ctx_list()
                    try:
                        modal.destroy()
                    except Exception:
                        pass

                threading.Thread(target=_do_enhance, daemon=True).start()

            save_btn = ctk.CTkButton(
                modal, text="Save & Enhance Preset", width=180, height=36,
                fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
                command=_save_modal_preset
            )
            save_btn.pack(pady=(15, 10))

        # Replaced inline frame with a single button
        ctk.CTkButton(
            form, text="+ Create Custom Preset", height=32,
            fg_color="transparent", border_width=1,
            text_color=(_ACCENT, "#7aaeff"),
            command=_open_add_preset_modal
        ).pack(anchor="w", padx=4, pady=(8, 8))

        # ── Save button ──
        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x", padx=30, pady=12)

        def _save() -> None:
            # App settings
            new = settings_module.load()
            new["hotkey"]          = hotkey_var.get().strip()
            new["check_mode"]      = mode_var.get()
            new["appearance_mode"] = appear_var.get().lower()
            new["auto_start"]      = autostart_var.get()
            new["save_history"]    = history_var.get()
            try:
                new["max_concurrent_scans"] = int(concurrent_var.get())
            except ValueError:
                new["max_concurrent_scans"] = 3
            settings_module.save(new)

            # Provider config
            lbl      = provider_var.get()
            pid      = _pid_list[_plbl_list.index(lbl)]
            save_provider_config({
                "provider": pid,
                "model":    model_var.get().strip(),
                "api_key":  key_var.get().strip(),
            })

            ctk.set_appearance_mode(new["appearance_mode"])

            if new["auto_start"]:
                autostart.enable()
            else:
                autostart.disable()

            # Mark home dirty so provider badge + hotkey update on next visit
            self._home_dirty = True

            # Visual confirmation
            save_btn.configure(text="✓  Saved!", fg_color="#27ae60")
            self._root.after(2000, lambda: save_btn.configure(text="Save Changes", fg_color=_ACCENT))

        save_btn = ctk.CTkButton(btn_row, text="Save Changes", width=140,
                                 fg_color=_ACCENT, hover_color=_ACCENT_HOVER, command=_save)
        save_btn.pack(side="right", padx=4)

        return outer

    def _show_settings(self) -> None:
        self._set_nav_active("settings")
        self._settings_panel.tkraise()

    # ── Window state ────────────────────────────────────────────────────────

    def show(self) -> None:
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def hide(self) -> None:
        self._root.withdraw()

    def toggle(self) -> None:
        if self._root.state() == "withdrawn":
            self.show()
        else:
            self.hide()

    def navigate(self, tab: str) -> None:
        """Switch to a named tab: 'home' | 'history' | 'settings'."""
        self.show()
        {"home": self._show_home, "history": self._show_history, "settings": self._show_settings}.get(tab, self._show_home)()
