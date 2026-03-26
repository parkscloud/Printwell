# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Run from source (from project root)
PYTHONPATH=src python -m printwell

# Run with a file argument (simulates file association)
PYTHONPATH=src python -m printwell path/to/file.md

# Build installer (two steps)
build.bat                                                    # PyInstaller → dist\Printwell\
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss # Inno Setup → installer_output\PrintwellSetup.exe
```

## Version

Version must be updated in **three places** before a release:
1. `src/printwell/__init__.py` — `__version__`
2. `src/printwell/constants.py` — `APP_VERSION`
3. `installer.iss` — `AppVersion`

## Architecture

**Flow:** Markdown → HTML (markdown2) → PDF (xhtml2pdf) or clipboard (CF_HTML via win32clipboard).

- **app.py** — Orchestrator. Creates a DnD-enabled root window (`DnDCTk` mixin combining `ctk.CTk` + `TkinterDnD.DnDWrapper`), starts pystray tray icon in a daemon thread, builds the main window. Close minimizes to tray; "Quit" from tray exits. Command-line `.md` argument auto-loads.
- **converter/markdown_parser.py** — `md_to_html()` produces an HTML fragment; `wrap_html()` wraps it in a full document with CSS.
- **converter/pdf_writer.py** — Registers bundled JetBrains Mono fonts with reportlab and xhtml2pdf, then renders HTML to PDF.
- **converter/clipboard.py** — Inlines styles on HTML elements, converts `\n` to `<br>` in `<pre>` blocks, then builds a CF_HTML envelope for the Windows clipboard.
- **ui/main_window.py** — Builds all widgets into the root window (not a Toplevel). Handles browse, drag-drop, preview, PDF export (threaded), and clipboard copy.

## Critical Workarounds

**Font registration (pdf_writer.py):** xhtml2pdf's `@font-face` CSS fails on Windows with `PermissionError` when it copies fonts to temp files. Fix: read `.ttf` into `BytesIO`, pass to reportlab `TTFont`, and inject entries into `xhtml2pdf.default.DEFAULT_FONT` dict so CSS `font-family` resolves. Do not use `@font-face` or file-path-based font loading.

**Clipboard styles (clipboard.py):** Word and Outlook ignore `<style>` blocks in pasted CF_HTML. All critical styles must be inlined on the elements themselves (`<pre>`, `<code>`, `<table>`, `<th>`, `<td>`, headings, blockquotes). Newlines in `<pre>` must be replaced with `<br>` or Word renders them as paragraph breaks with extra spacing.

**Drag-and-drop (app.py):** `ctk.CTk` doesn't support tkinterdnd2 natively. The `DnDCTk` class uses multiple inheritance to mix in `TkinterDnD.DnDWrapper`. The main window builds into this root directly (not a Toplevel) so DnD events propagate. Falls back to browse-only if tkinterdnd2 is unavailable.

## PyInstaller Bundling

The spec (`Printwell.spec`) must `collect_all` for: customtkinter, tkinterdnd2, xhtml2pdf, **and reportlab** (reportlab.graphics.barcode submodules are dynamically imported and missed otherwise). Fonts and the `.ico` are bundled as data files under `printwell/`.

## Style Conventions

This project matches **Hearsay** (parkscloud/Hearsay) in code style, README structure, and build toolchain:
- `from __future__ import annotations` in all modules
- `log = logging.getLogger(__name__)` per module
- Type hints throughout, `Path` over string paths
- customtkinter dark theme + blue color scheme
- PDF code blocks: white background, dark text, no borders (not dark theme)
