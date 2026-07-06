# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# First-time setup
pip install -r requirements.txt

# Run from source (from project root)
PYTHONPATH=src python -m printwell

# Run with a file argument (simulates file association)
PYTHONPATH=src python -m printwell path/to/file.md

# Start hidden in the tray (what the installer's startup shortcut passes)
PYTHONPATH=src python -m printwell --minimized

# Build installer (two steps)
build.bat                                                    # PyInstaller → dist\Printwell\
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss # Inno Setup → installer_output\PrintwellSetup.exe
```

There is no test suite. Verify changes by running the app manually and exercising the affected flow (browse, drag-drop, preview, PDF export, clipboard copy). Window-state behavior (tray/minimized/visible) can be verified programmatically: enumerate top-level windows for the app's PID via Win32 `EnumWindows`, filter window class `TkTopLevel`, and assert `IsWindowVisible`; confirm drag-drop coverage by counting "OLE drop target registered" lines in `%APPDATA%\Printwell\logs\printwell_YYYY-MM-DD.log` (27 HWNDs as of v1.0.3 — the count should match between normal and `--minimized` launches).

Release process (build → Inno Setup → `gh release create`) is documented in `RELEASING.md`.

ISCC emits a `UsedUserAreasWarning` (per-user areas used with `PrivilegesRequired=admin`) — expected, do not "fix": the uninstaller intentionally clears `%APPDATA%\Printwell`.

## Version

Version must be updated in **three places** before a release:
1. `src/printwell/__init__.py` — `__version__`
2. `src/printwell/constants.py` — `APP_VERSION`
3. `installer.iss` — `AppVersion`

**Never change `AppId` in `installer.iss`.** The GUID (pinned in v1.0.3) is the app's permanent identity in Windows' Add/Remove Programs registry. Changing it makes Windows treat existing installs as a different product — upgrades stop being recognized and users must manually uninstall the orphaned entry.

## Architecture

**Flow:** Markdown → HTML (markdown2) → PDF (xhtml2pdf) or clipboard (CF_HTML via win32clipboard).

- **app.py** — Orchestrator. Creates a `ctk.CTk` root window, starts pystray tray icon in a daemon thread, builds the main window. Close minimizes to tray; "Quit" from tray exits. Command-line `.md` argument auto-loads; `--minimized` starts withdrawn to the tray (a file argument overrides it).
- **converter/markdown_parser.py** — `md_to_html()` produces an HTML fragment; `wrap_html()` wraps it in a full document with CSS.
- **converter/pdf_writer.py** — Registers bundled JetBrains Mono fonts with reportlab and xhtml2pdf, then renders HTML to PDF.
- **converter/clipboard.py** — Inlines styles on HTML elements, converts `\n` to `<br>` in `<pre>` blocks, then builds a CF_HTML envelope for the Windows clipboard.
- **ui/main_window.py** — Builds all widgets directly into the root window, not a `Toplevel`. This was originally required for tkinterdnd2's `DnDWrapper`; it's kept because the current OLE drop target also benefits from a stable top-level HWND to register against. Handles browse, drag-drop, preview, PDF export (Save As dialog, threaded), and clipboard copy.
- **utils/drop_target.py** — OLE IDropTarget implemented with ctypes. Handles Explorer file drops (CF_HDROP) and Outlook attachment drops (FileGroupDescriptorW/FileContents virtual-file protocol). Registers on all ancestor and child HWNDs of the root window.
- **config.py + utils/paths.py + utils/logging_setup.py** — `ConfigManager` persists app config and logs under `%APPDATA%\Printwell\`. The Inno Setup uninstaller clears this directory, so do not store user data elsewhere.

**Tray-to-UI thread safety:** The pystray icon runs in a daemon thread. Any UI work triggered from tray callbacks must be marshalled onto the Tk thread via `self._root.after(0, ...)` — see `PrintwellApp._show_window` / `_open_about`. Calling Tk widgets directly from the tray thread will crash or deadlock. The same rule applies to any future background threads (e.g. the PDF export worker in `main_window.py`).

## Critical Workarounds

**Font registration (pdf_writer.py):** xhtml2pdf's `@font-face` CSS fails on Windows with `PermissionError` when it copies fonts to temp files. Fix: read `.ttf` into `BytesIO`, pass to reportlab `TTFont`, and inject entries into `xhtml2pdf.default.DEFAULT_FONT` dict so CSS `font-family` resolves. Do not use `@font-face` or file-path-based font loading.

**Clipboard styles (clipboard.py):** Word and Outlook ignore `<style>` blocks in pasted CF_HTML. All critical styles must be inlined on the elements themselves (`<pre>`, `<code>`, `<table>`, `<th>`, `<td>`, headings, blockquotes). Newlines in `<pre>` must be replaced with `<br>` or Word renders them as paragraph breaks with extra spacing.

**Drag-and-drop (utils/drop_target.py):** OLE IDropTarget is implemented entirely with ctypes, bypassing pywin32's COM gateway (which wraps objects in a `DesignatedWrapPolicy` that doesn't forward vtable method calls). The drop target is registered on all ancestor and child HWNDs of the root window to ensure the correct window receives drag events regardless of customtkinter's internal window hierarchy. Supports both CF_HDROP (Explorer) and FileGroupDescriptorW/FileContents (Outlook virtual files). Before enumerating, `main_window._setup_drop_target` walks the widget tree calling `winfo_id()` to force HWND creation: a `--minimized` start leaves the window withdrawn and never mapped, so child HWNDs don't exist yet and `EnumChildWindows` would silently miss them, breaking drag-drop for tray-started sessions.

## PyInstaller Bundling

The spec (`Printwell.spec`) must `collect_all` for: customtkinter, xhtml2pdf, **and reportlab** (reportlab.graphics.barcode submodules are dynamically imported and missed otherwise). Fonts and the `.ico` are bundled as data files under `printwell/`.

## Style Conventions

This project matches **Hearsay** (parkscloud/Hearsay) in code style, README structure, and build toolchain:
- `from __future__ import annotations` in all modules
- `log = logging.getLogger(__name__)` per module
- Type hints throughout, `Path` over string paths
- customtkinter dark theme + blue color scheme
- PDF code blocks: white background, dark text, no borders (not dark theme)
