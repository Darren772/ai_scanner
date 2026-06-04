<div align="center">

# renScan

### Screen-Capture AI Proofreading Tool

**Technical Program Documentation — v1.0 · 2025**

`Python 3.10+` &nbsp;·&nbsp; `CustomTkinter` &nbsp;·&nbsp; `MSS` &nbsp;·&nbsp; `Pillow` &nbsp;·&nbsp; `Gemini Vision API`

---

*Classification: Confidential · Internal Use Only*

</div>

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [End-to-End User Flow](#2-end-to-end-user-flow)
3. [Feature Specifications](#3-feature-specifications)
   - 3.1 [Global Hotkey System](#31-global-hotkey-system)
   - 3.2 [Screen Overlay](#32-screen-overlay)
   - 3.3 [Screenshot Capture](#33-screenshot-capture)
   - 3.4 [Check Modes](#34-check-modes)
   - 3.5 [Gemini Vision API Integration](#35-gemini-vision-api-integration)
   - 3.6 [Floating Results Panel](#36-floating-results-panel)
   - 3.7 [System Tray](#37-system-tray)
   - 3.8 [Settings Window](#38-settings-window)
   - 3.9 [History Log](#39-history-log)
4. [UI Design — CustomTkinter](#4-ui-design--customtkinter)
   - 4.1 [Why CustomTkinter](#41-why-customtkinter)
   - 4.2 [CTk Widget Map](#42-ctk-widget-map)
   - 4.3 [Theming Setup](#43-theming-setup)
   - 4.4 [Overlay — Special Case](#44-overlay--special-case)
5. [Architecture & Project Structure](#5-architecture--project-structure)
   - 5.1 [Layer Order](#51-layer-order)
   - 5.2 [File Tree](#52-file-tree)
   - 5.3 [Key Data Class](#53-key-data-class)
6. [Data Flow & Privacy Model](#6-data-flow--privacy-model)
   - 6.1 [Temp File Lifecycle](#61-temp-file-lifecycle)
7. [Dependencies](#7-dependencies)
8. [Setup & Installation](#8-setup--installation)
   - 8.1 [Prerequisites](#81-prerequisites)
   - 8.2 [Install Steps](#82-install-steps)
   - 8.3 [First-Run Checklist](#83-first-run-checklist)
9. [Configuration Reference](#9-configuration-reference)
10. [Extension Guide](#10-extension-guide)
11. [Known Limitations](#11-known-limitations)
12. [Version History](#12-version-history)

---

## 1. Executive Summary

renScan is a **privacy-first desktop utility** for Windows, macOS, and Linux that provides AI-powered proofreading without ever exposing your source document to any external system.

The user invokes a global hotkey, draws a selection box over any region of their screen, and receives structured **grammar, spelling, structure, and tone feedback** in a floating panel — all within seconds.

> **Core insight:** A screenshot of text is fundamentally different from the document file itself. renScan never opens, reads, or transmits your document. It only captures what you explicitly select on screen, sends that image to the Gemini Vision API via your own personal API key, and immediately deletes the temporary file after the response is received.

### Problem Statement

| Pain Point | Detail |
|---|---|
| **Privacy risk** | Copy-pasting text into a web AI interface leaks the full document to a third-party service |
| **High friction** | Switching between a document and an AI chat window breaks reading flow |
| **No existing tool** | No utility provides inline AI feedback on arbitrary screen regions of any application |

### Solution

| Benefit | How |
|---|---|
| **One hotkey → result in < 5s** | Hotkey → draw box → results appear |
| **Document never leaves machine** | Only a cropped screenshot is transmitted |
| **No window switching** | Floating panel sits on top of your document |
| **Fast & cheap** | Powered by Gemini 1.5 Flash |
| **Fully configurable** | Check modes, hotkeys, history, privacy settings |

---

## 2. End-to-End User Flow

```
[User] Ctrl+Shift+S
    │
    ▼
[Overlay opens] Fullscreen transparent dark layer
    │
    ▼
[User draws selection box] Click + drag over text
    │
    ▼
[capture.py] mss captures region → /tmp/renscan_abc123.png
    │
    ▼
[results_panel.py] Floating CTk panel opens with spinner
    │
    ▼
[gemini.py] PNG + prompt → POST api.generativelanguage.googleapis.com
    │
    ▼
[checker.py] parse_response() → CheckResult dataclass
    │
    ├── [capture.py] delete_temp() — PNG deleted (privacy mode)
    ├── [log.py] append() — text-only entry saved (if enabled)
    │
    ▼
[results_panel.py] Panel fills with Grammar / Spelling / Structure / Tone / Rewrite
```

### Step-by-Step Table

| # | Step | Actor | Detail |
|---|---|---|---|
| 1 | Hotkey trigger | User | Presses `Ctrl+Shift+S`. App wakes from tray. |
| 2 | Overlay opens | renScan | Fullscreen transparent dark overlay covers all monitors. |
| 3 | Region selection | User | Clicks and drags to draw a box over target text. |
| 4 | Screenshot capture | renScan | `mss` captures the selected region. Saved as temp PNG in `/tmp`. |
| 5 | Loading state | renScan | Floating CTk panel appears immediately with a spinner. |
| 6 | API call | renScan | Image + prompt POSTed to Gemini 1.5 Flash via personal API key. |
| 7 | Response parsing | renScan | Raw text split into Grammar / Spelling / Structure / Tone / Rewrite. |
| 8 | Results displayed | renScan | CTk panel fills with categorised, copyable suggestions. |
| 9 | Temp file deleted | renScan | Screenshot PNG deleted immediately (privacy mode). |
| 10 | Log entry written | renScan | Text-only result appended to `history/log.json` (if enabled). |

---

## 3. Feature Specifications

### 3.1 Global Hotkey System

renScan listens for keyboard shortcuts globally — even when no window is in focus — using the `keyboard` library running in a dedicated background thread.

| Shortcut | Action | Configurable |
|---|---|---|
| `Ctrl + Shift + S` | Open screen overlay | ✅ Yes |
| `Esc` | Cancel overlay / close results panel | ❌ No |
| `Ctrl + C` | Copy full result to clipboard (panel open) | ❌ No |
| `Ctrl + Shift + H` | Open history window | ✅ Yes |

> **⚠️ Platform notes**
> - **Linux:** The `keyboard` library may require `sudo` on some distros.
> - **macOS:** The app must be granted Accessibility permissions in System Settings.
> - **Windows:** No special permissions required.

---

### 3.2 Screen Overlay

A frameless, fullscreen CustomTkinter window that covers all connected monitors.

- Background: semi-transparent dark fill (`rgba 0,0,0,0.45`) — underlying content remains readable
- Cursor changes to `crosshair` on entry, restores on exit
- Selection box drawn with a 2px `#1A56DB` border and light blue semi-transparent fill
- **Live dimension label** shows `width × height` near the bottom-right of the selection
- `Esc` or right-click cancels with no side effects
- Mouse release fires `on_select(x, y, w, h)` callback and closes the overlay

---

### 3.3 Screenshot Capture

Handled by `core/capture.py`. Uses `mss` for fast, cross-platform, multi-monitor screen capture.

- Accepts `(x, y, width, height)` in absolute screen coordinates
- Handles multi-monitor setups by mapping coordinates to the correct display
- Saves to Python's `tempfile.mkstemp()` — never to the document directory
- Returns the full temp PNG path to the caller
- `delete_temp(path)` is called immediately after API response in privacy mode

---

### 3.4 Check Modes

| Mode | Prompt Focus | Result Sections |
|---|---|---|
| **Full** *(default)* | Comprehensive review of all dimensions | Grammar, Spelling, Structure, Tone, Rewrite |
| **Grammar** | Sentence structure, tense, subject-verb agreement | Grammar, Rewrite |
| **Spelling** | Typos, misspellings, homophone errors | Spelling, Rewrite |
| **Structure** | Paragraph flow, logical order, transitions | Structure, Rewrite |
| **Tone** | Formality, active/passive voice, word choice | Tone, Rewrite |

---

### 3.5 Gemini Vision API Integration

Handled by `api/gemini.py`. Uses the official `google-generativeai` SDK.

- **Model:** `gemini-1.5-flash` — optimised for speed and multimodal input
- Single API call: image bytes + structured prompt sent together
- No separate OCR step — Gemini reads text directly from the image
- `parse_response()` splits raw text by section headers into a structured dict
- API key loaded from `.env` via `python-dotenv` — never hardcoded

#### Prompt Structure (Full Mode)

```
You are a professional editor. Read the text in the image carefully.
Return your feedback in exactly these labelled sections:

## GRAMMAR
List each grammar issue on a new line, prefixed with a dash.

## SPELLING
List each spelling error on a new line, prefixed with a dash.

## STRUCTURE
List each structure/flow suggestion on a new line, prefixed with a dash.

## TONE
List each tone observation on a new line, prefixed with a dash.

## REWRITE
Provide a clean corrected version of the full text.

If a section has no issues, write "None found." under that heading.
```

---

### 3.6 Floating Results Panel

The most user-facing component. A CustomTkinter frameless window that sits always-on-top of other applications.

- **Frameless** — no OS title bar, fully custom header
- **Draggable** — click-and-drag the header bar to reposition
- **Always-on-top** — `CTkToplevel` with `wm_attributes('-topmost', True)`
- **Tab bar** — `Grammar | Spelling | Structure | Tone | Rewrite` via `CTkTabview`
- **Scrollable sections** — `CTkScrollableFrame` with one `CTkFrame` per suggestion
- **Per-item copy** — `CTkButton` with icon on every suggestion
- **Footer** — `Copy All` and `Copy Rewrite` buttons
- **Loading state** — `CTkProgressBar` (indeterminate) + label during API call
- **Dismiss** — `Esc` or close button destroys the window

---

### 3.7 System Tray

- Powered by `pystray` — runs in a daemon thread
- Icon: `assets/icon.png` (64×64 PNG — replace with your branding)
- Right-click menu:

```
renScan
─────────────────
Open Settings
View History
─────────────────
Quit
```

- App starts **minimised to tray** on launch — no window shown on startup

---

### 3.8 Settings Window

A `CTkToplevel` window for all user preferences. Persisted to `config/user_settings.json` on Save.

| Field | Widget | Default |
|---|---|---|
| Gemini API key | `CTkEntry(show='*')` + toggle | *Empty — required* |
| Hotkey | `CTkEntry` + Record button | `ctrl+shift+s` |
| Check mode | `CTkOptionMenu` | `Full` |
| Auto-start on boot | `CTkSwitch` | Off |
| Save history | `CTkSwitch` | On |
| Privacy mode | `CTkSwitch` *(disabled — locked on)* | On |
| Appearance mode | `CTkSegmentedButton`: Light / Dark / System | System |

---

### 3.9 History Log

- Stored in `history/log.json` — **text only, no images ever saved**
- Each entry: `id` (UUID), `timestamp` (ISO 8601), `mode`, full `result` object
- History viewer: `CTkScrollableFrame` listing entries by timestamp
- Click an entry → expands in a detail pane on the right
- Per-entry delete button; `Clear All` wipes the file
- Feature can be **fully disabled** from Settings

---

## 4. UI Design — CustomTkinter

renScan replaces standard `tkinter` with **CustomTkinter (CTk)** throughout, giving the app a modern polished look with rounded widgets, smooth theming, and a built-in dark/light mode toggle — with no additional styling code.

### 4.1 Why CustomTkinter

| Feature | Detail |
|---|---|
| Drop-in replacement | Same geometry managers, same event loop as tkinter |
| Modern aesthetics | Rounded corners, flat design, hover effects out of the box |
| Built-in theming | `ctk.set_appearance_mode('dark'/'light'/'system')` |
| Built-in colour themes | `'blue'` / `'green'` / `'dark-blue'` |
| No custom styling | No `ttk.Style()` or manual `Canvas` drawing needed |
| Active project | [github.com/TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) |

---

### 4.2 CTk Widget Map

| UI Element | CTk Class | Notes |
|---|---|---|
| Main windows | `CTkToplevel` | Frameless, topmost, draggable via `bind('<B1-Motion>')` |
| Buttons | `CTkButton` | Rounded corners, hover colour, optional image/icon |
| Text inputs | `CTkEntry` | Rounded, `placeholder_text` support |
| Dropdowns | `CTkOptionMenu` | Replaces `tk.OptionMenu` with modern styling |
| Toggle switches | `CTkSwitch` | Replaces checkboxes for settings toggles |
| Tab navigation | `CTkTabview` | Built-in tab bar for results panel sections |
| Scrollable lists | `CTkScrollableFrame` | Auto-scrollbar — used in history and results |
| Progress / loading | `CTkProgressBar` | Indeterminate mode for API loading state |
| Labels | `CTkLabel` | Supports `wraplength`, `image`, `compound` |
| Segmented control | `CTkSegmentedButton` | Used for Light / Dark / System appearance selector |
| Frames / panels | `CTkFrame` | Rounded container, supports `fg_color` |

---

### 4.3 Theming Setup

Set once in `main.py` before any CTk window is created:

```python
import customtkinter as ctk

ctk.set_appearance_mode("system")      # "light" | "dark" | "system"
ctk.set_default_color_theme("blue")    # "blue" | "green" | "dark-blue"

# To switch at runtime (e.g. from the settings window):
ctk.set_appearance_mode(new_mode)
```

---

### 4.4 Overlay — Special Case

The screen overlay does **not** use CustomTkinter because it needs pixel-perfect transparency and a `Canvas` for rubber-band drawing. It uses raw `tkinter`:

```python
import tkinter as tk

root = tk.Tk()
root.attributes("-fullscreen", True)
root.attributes("-alpha", 0.35)        # semi-transparent
root.attributes("-topmost", True)
root.config(cursor="crosshair")
root.config(bg="black")

canvas = tk.Canvas(root, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)

# Draw rubber-band rect during mouse drag:
rect = canvas.create_rectangle(x1, y1, x2, y2,
    outline="#1A56DB", width=2, fill="#1A56DB", stipple="gray25")
```

---

## 5. Architecture & Project Structure

renScan follows a strict **layered architecture**. UI code never contains business logic, and business logic never imports from the UI layer.

### 5.1 Layer Order

```
main.py
  │
  ├── ui/          ← CustomTkinter windows only. Imports from core/ and utils/.
  │
  ├── core/        ← Orchestration, capture, hotkey. Imports from api/ and utils/.
  │
  ├── api/         ← Gemini client. No dependencies on other local modules.
  │
  ├── history/     ← Local persistence. No dependencies on other local modules.
  │
  ├── utils/       ← Pure helpers. No local imports.
  │
  └── config/      ← Settings and prompts. No local imports.
```

**Dependency flow is strictly top-down. No circular imports.**

---

### 5.2 File Tree

```
renscan/
├── main.py                     # Entry point. Boot: settings → hotkey → tray → mainloop
├── requirements.txt            # pip dependencies
├── .env                        # GEMINI_API_KEY=... (never commit)
├── .env.example                # Template — copy to .env and fill key
│
├── config/
│   ├── __init__.py
│   ├── settings.py             # load() / save() — persists to user_settings.json
│   └── prompts.py              # One prompt function per check mode
│
├── core/
│   ├── __init__.py
│   ├── hotkey.py               # register(hotkey, callback) in background thread
│   ├── capture.py              # capture_region(x,y,w,h) → temp PNG path
│   └── checker.py              # run(image_path, mode) → CheckResult
│
├── api/
│   ├── __init__.py
│   └── gemini.py               # send(image_path, prompt) → str
│                               # parse_response(raw) → dict
│
├── ui/
│   ├── __init__.py
│   ├── overlay.py              # Raw tkinter fullscreen canvas overlay
│   ├── results_panel.py        # CTkToplevel floating results panel
│   ├── settings_window.py      # CTkToplevel settings form
│   ├── history_window.py       # CTkToplevel history viewer
│   └── tray.py                 # pystray tray icon in daemon thread
│
├── utils/
│   ├── __init__.py
│   ├── clipboard.py            # copy(text) via tkinter clipboard
│   ├── autostart.py            # enable() / disable() / is_enabled()
│   └── logger.py               # info() / error() → renscan.log
│
├── history/
│   ├── __init__.py
│   └── log.py                  # append() / load_all() / delete(id) / clear()
│
└── assets/
    └── icon.png                # 64×64 tray icon — replace with your branding
```

---

### 5.3 Key Data Class

`CheckResult` is the central object passed between `core/`, `api/`, and `ui/`:

```python
from dataclasses import dataclass, field

@dataclass
class CheckResult:
    grammar:   list[str] = field(default_factory=list)
    spelling:  list[str] = field(default_factory=list)
    structure: list[str] = field(default_factory=list)
    tone:      list[str] = field(default_factory=list)
    rewrite:   str = ""
    raw:       str = ""   # original Gemini response — for debugging
```

---

## 6. Data Flow & Privacy Model

renScan operates under a strict privacy contract.

### What NEVER leaves your machine ✅

| Data | Location |
|---|---|
| Your source document | Never read or accessed by renScan |
| User settings | `config/user_settings.json` — local only |
| History log | `history/log.json` — local only, text only |
| Gemini API key | `.env` — local only |
| Debug log | `renscan.log` — local only |
| Temp screenshot | Deleted immediately after API response |

### What is sent to Google ⚠️

| Data | Detail |
|---|---|
| Screenshot PNG bytes | Only the region you explicitly selected on screen |
| Prompt string | The text in `config/prompts.py` |
| API key | Sent as `Authorization` header to `api.generativelanguage.googleapis.com` |

> **Note:** Data handling is governed by Google's [Gemini API Terms of Service](https://ai.google.dev/terms). Review before using on highly sensitive material.

---

### 6.1 Temp File Lifecycle

```python
# core/capture.py
tmp_path = capture_region(x, y, w, h)       # → /tmp/renscan_abc123.png

# core/checker.py
result = api.gemini.send(tmp_path, prompt)   # ← image sent here

if settings["privacy_mode"]:                 # always True by default
    capture.delete_temp(tmp_path)            # ← file deleted here

# tmp_path is now gone. result is pure text.
history.log.append(mode, result)             # text only, no image reference
```

---

## 7. Dependencies

| Package | Version | Purpose |
|---|---|---|
| `customtkinter` | 5.x | Modern UI widgets — `CTkButton`, `CTkFrame`, `CTkTabview`, etc. |
| `google-generativeai` | 0.5+ | Official Gemini SDK for Vision API calls |
| `Pillow` | 10.x | Image processing — format conversion, resize |
| `mss` | 9.x | Fast cross-platform multi-monitor screen capture |
| `keyboard` | 0.13+ | Global hotkey registration in background thread |
| `pystray` | 0.19+ | System tray icon and right-click menu |
| `python-dotenv` | 1.x | Load `GEMINI_API_KEY` from `.env` file |

Install all with:

```bash
pip install -r requirements.txt
```

> **Linux only:** `sudo apt install python3-tk python3-dev` is required for tkinter on Ubuntu/Debian. Some distros also need `pip install xlib` for the `keyboard` library.

---

## 8. Setup & Installation

### 8.1 Prerequisites

- Python **3.10** or higher
- A Gemini API key — free at [aistudio.google.com](https://aistudio.google.com)
- Windows 10/11, macOS 12+, or Ubuntu 20.04+

---

### 8.2 Install Steps

**Step 1 — Unzip the project**

```bash
unzip renscan.zip -d renscan
cd renscan
```

**Step 2 — Create a virtual environment** *(recommended)*

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**Step 3 — Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 4 — Configure your Gemini API key**

```bash
cp .env.example .env
# Open .env and set:
# GEMINI_API_KEY=your_actual_key_here
```

**Step 5 — Run**

```bash
python main.py
# App starts silently in the system tray.
# Press Ctrl+Shift+S to make your first capture.
```

---

### 8.3 First-Run Checklist

1. Right-click the tray icon → **Open Settings**
2. Paste your Gemini API key and click **Save**
3. Open any document in any application
4. Press `Ctrl+Shift+S`, draw a box over a paragraph, check the result
5. *(Optional)* Enable **Auto-start** in Settings so renScan launches with your system

---

## 9. Configuration Reference

All settings are stored in `config/user_settings.json`, managed through the Settings window, and created automatically on first run.

| Key | Type | Default | Description |
|---|---|---|---|
| `hotkey` | `string` | `"ctrl+shift+s"` | Global hotkey to trigger the overlay |
| `check_mode` | `string` | `"full"` | `"full"` \| `"grammar"` \| `"spelling"` \| `"structure"` \| `"tone"` |
| `auto_start` | `boolean` | `false` | Add renScan to OS startup programs |
| `save_history` | `boolean` | `true` | Append results to `history/log.json` |
| `privacy_mode` | `boolean` | `true` | Delete temp screenshot after API response |
| `appearance_mode` | `string` | `"system"` | `"light"` \| `"dark"` \| `"system"` |
| `color_theme` | `string` | `"blue"` | `"blue"` \| `"green"` \| `"dark-blue"` |

**Example `user_settings.json`:**

```json
{
  "hotkey": "ctrl+shift+s",
  "check_mode": "full",
  "auto_start": false,
  "save_history": true,
  "privacy_mode": true,
  "appearance_mode": "dark",
  "color_theme": "blue"
}
```

---

## 10. Extension Guide

### 10.1 Swap to a Different AI Model

All API logic is isolated in `api/gemini.py`. Replace `send()` and `parse_response()`. The rest of the codebase only ever sees a `CheckResult` object.

| Model | SDK / Method |
|---|---|
| OpenAI GPT-4o | `openai` SDK with vision message content |
| Anthropic Claude | `anthropic` SDK with image content blocks |
| Local (Ollama + LLaVA) | `HTTP POST` to `localhost:11434/api/generate` |

---

### 10.2 Add a New Check Mode

1. Add a new prompt function in `config/prompts.py`
2. Add the mode name to `DEFAULTS` in `config/settings.py`
3. Add it to the `CTkOptionMenu` values in `ui/settings_window.py`
4. Handle the new key in `core/checker.py run()`

---

### 10.3 Multilingual Support

Modify prompt templates in `config/prompts.py` to instruct Gemini to respond in a target language, or auto-detect from the image:

```python
def full_check(language: str = "auto") -> str:
    lang_instruction = (
        f"Respond in {language}."
        if language != "auto"
        else "Detect the language of the text and respond in the same language."
    )
    return f"{lang_instruction}\n\nYou are a professional editor..."
```

---

### 10.4 Export History

Add an Export button in `ui/history_window.py`:

```python
import csv, json

def export_csv(path: str) -> None:
    entries = history.log.load_all()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp","mode","grammar","spelling","rewrite"])
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "timestamp": e["timestamp"],
                "mode":      e["mode"],
                "grammar":   "\n".join(e["result"]["grammar"]),
                "spelling":  "\n".join(e["result"]["spelling"]),
                "rewrite":   e["result"]["rewrite"],
            })
```

---

### 10.5 Package as a Standalone Executable

```bash
pip install pyinstaller

pyinstaller \
  --onefile \
  --windowed \
  --icon=assets/icon.png \
  --add-data "assets:assets" \
  main.py

# Output:
#   Windows → dist/main.exe
#   macOS   → dist/main
#   Linux   → dist/main
```

---

## 11. Known Limitations

| Limitation | Detail |
|---|---|
| Small text accuracy | Text < 8pt on screen may not be read accurately by Gemini Vision |
| Stylised fonts | Handwritten or decorative fonts may produce lower quality results |
| macOS hotkeys | The `keyboard` library does not support all key combinations on macOS |
| Multi-monitor overlay | Covers the primary monitor only by default (extendable in `ui/overlay.py`) |
| Internet required | Gemini API calls require an active connection — no offline mode |
| History encryption | `log.json` is plain text — disable history if result text is sensitive |

---

## 12. Version History

| Version | Date | Notes |
|---|---|---|
| `1.0.0` | 2025 | Initial release — overlay, Gemini Vision, CTk results panel, tray, settings, history, privacy mode |

---

<div align="center">

renScan &nbsp;·&nbsp; Technical Program Documentation &nbsp;·&nbsp; v1.0 &nbsp;·&nbsp; 2025

*Confidential · Internal Use Only*

</div>
