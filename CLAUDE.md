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

- **app.py** — Orchestrator. Creates a `ctk.CTk` root window, starts pystray tray icon in a daemon thread, builds the main window. Close minimizes to tray; "Quit" from tray exits. Command-line `.md` argument auto-loads.
- **converter/markdown_parser.py** — `md_to_html()` produces an HTML fragment; `wrap_html()` wraps it in a full document with CSS.
- **converter/pdf_writer.py** — Registers bundled JetBrains Mono fonts with reportlab and xhtml2pdf, then renders HTML to PDF.
- **converter/clipboard.py** — Inlines styles on HTML elements, converts `\n` to `<br>` in `<pre>` blocks, then builds a CF_HTML envelope for the Windows clipboard.
- **ui/main_window.py** — Builds all widgets into the root window (not a Toplevel). Handles browse, drag-drop (via OLE drop target), preview, PDF export (Save As dialog, threaded), and clipboard copy.
- **utils/drop_target.py** — OLE IDropTarget implemented with ctypes. Handles Explorer file drops (CF_HDROP) and Outlook attachment drops (FileGroupDescriptorW/FileContents virtual-file protocol). Registers on all ancestor and child HWNDs of the root window.

## Critical Workarounds

**Font registration (pdf_writer.py):** xhtml2pdf's `@font-face` CSS fails on Windows with `PermissionError` when it copies fonts to temp files. Fix: read `.ttf` into `BytesIO`, pass to reportlab `TTFont`, and inject entries into `xhtml2pdf.default.DEFAULT_FONT` dict so CSS `font-family` resolves. Do not use `@font-face` or file-path-based font loading.

**Clipboard styles (clipboard.py):** Word and Outlook ignore `<style>` blocks in pasted CF_HTML. All critical styles must be inlined on the elements themselves (`<pre>`, `<code>`, `<table>`, `<th>`, `<td>`, headings, blockquotes). Newlines in `<pre>` must be replaced with `<br>` or Word renders them as paragraph breaks with extra spacing.

**Drag-and-drop (utils/drop_target.py):** OLE IDropTarget is implemented entirely with ctypes, bypassing pywin32's COM gateway (which wraps objects in a `DesignatedWrapPolicy` that doesn't forward vtable method calls). The drop target is registered on all ancestor and child HWNDs of the root window to ensure the correct window receives drag events regardless of customtkinter's internal window hierarchy. Supports both CF_HDROP (Explorer) and FileGroupDescriptorW/FileContents (Outlook virtual files).

## PyInstaller Bundling

The spec (`Printwell.spec`) must `collect_all` for: customtkinter, xhtml2pdf, **and reportlab** (reportlab.graphics.barcode submodules are dynamically imported and missed otherwise). Fonts and the `.ico` are bundled as data files under `printwell/`.

## Style Conventions

This project matches **Hearsay** (parkscloud/Hearsay) in code style, README structure, and build toolchain:
- `from __future__ import annotations` in all modules
- `log = logging.getLogger(__name__)` per module
- Type hints throughout, `Path` over string paths
- customtkinter dark theme + blue color scheme
- PDF code blocks: white background, dark text, no borders (not dark theme)
