# Printwell

**Windows desktop app that converts Markdown files to clean, formatted PDFs -- or copies the rich text to your clipboard for pasting into Word, Outlook, and more.**

Drop a file, get a PDF. No fuss, no cloud, no subscriptions.

---

## Features

- **Drag-and-drop or browse** -- navigate to a `.md` file or drop it straight onto the window; also accepts attachments dragged directly from Outlook
- **PDF export with Save As** -- choose where to save the PDF via a standard Save dialog (defaults to the source file's directory and name)
- **Rich text clipboard** -- copies the rendered Markdown as formatted text, ready to paste into Word, Outlook, Teams, etc.
- **System tray app** -- runs quietly in the tray, accessible from the taskbar or a desktop shortcut
- **Launches on startup** -- always ready when you need it
- **File association** -- optionally registers as the default app for `.md` files
- **Local and offline** -- everything runs on your machine, no API calls or cloud services
- **Dark theme UI** -- modern look consistent with the rest of the toolbox

## Quick Start

### From source

```bash
# Clone the repo
git clone https://github.com/parkscloud/Printwell.git
cd Printwell

# Install dependencies
pip install -r requirements.txt

# Run
python -m printwell
```

### Installed version

Download the latest installer from the [Releases](https://github.com/parkscloud/Printwell/releases) page and run `PrintwellSetup.exe`. The app appears in your Start Menu and Add/Remove Programs.

### Silent install (RMM / SCCM / Intune)

```
PrintwellSetup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Installs to `C:\Program Files\Printwell` for all users. Registers as default app for `.md` files and starts at login. To skip file association and auto-start:

```
PrintwellSetup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=""
```

Uninstall silently:

```
"C:\Program Files\Printwell\unins000.exe" /VERYSILENT
```

## Usage

1. **Launch** Printwell from the Start Menu or run from source
2. **Open a file** -- click Browse or drag a `.md` file onto the window
3. A preview of the rendered Markdown appears in the main panel
4. Click **Export PDF** -- a Save dialog opens, defaulting to the same name and directory as the source file
6. Click **Copy Rich Text** to put the formatted content on your clipboard, then paste into Word, Outlook, or anywhere that accepts rich text

## Project Structure

```
src/printwell/
├── __init__.py              # Version string
├── __main__.py              # Entry point
├── app.py                   # Application orchestrator
├── config.py                # AppConfig + ConfigManager
├── constants.py             # App name, defaults, colors
├── printwell.ico            # Application icon
├── converter/
│   ├── markdown_parser.py   # Markdown to HTML with CSS styling
│   ├── pdf_writer.py        # HTML to PDF (xhtml2pdf + bundled fonts)
│   └── clipboard.py         # Rich text clipboard copy (CF_HTML)
├── fonts/
│   ├── JetBrainsMono-*.ttf  # Bundled monospace font
│   └── OFL.txt              # SIL Open Font License
├── ui/
│   ├── main_window.py       # Main window (browse, drag-drop, preview, actions)
│   ├── dialogs.py           # Overwrite/rename confirmation
│   ├── tray.py              # System tray icon (pystray)
│   └── theme.py             # customtkinter dark + blue theme
└── utils/
    ├── drop_target.py       # OLE drag-and-drop (Explorer + Outlook attachments)
    ├── paths.py             # %APPDATA%\Printwell directories
    └── logging_setup.py     # File + console logging
```

## Building

### Prerequisites

1. **Python 3.11+**
2. **Project dependencies:** `pip install -r requirements.txt`
3. **PyInstaller:** `pip install pyinstaller`
4. **Inno Setup 6+:** `winget install JRSoftware.InnoSetup`

### Build steps

```bash
# 1. Bundle the app with PyInstaller (output in dist\Printwell\)
build.bat

# 2. Compile the Windows installer
iscc installer.iss
```

The installer is written to `installer_output\PrintwellSetup.exe`.

## Tech Stack

- **Python 3.11+**
- **markdown2** -- Markdown to HTML conversion with extras (tables, fenced code, etc.)
- **xhtml2pdf** -- HTML/CSS to PDF rendering
- **customtkinter** -- Modern dark-themed UI
- **pystray + Pillow** -- System tray icon
- **pywin32** -- Rich text clipboard and OLE drag-and-drop
- **PyInstaller + Inno Setup** -- Build and install
- **[JetBrains Mono](https://www.jetbrains.com/lp/mono/)** -- Bundled monospace font for code blocks ([OFL 1.1](src/printwell/fonts/OFL.txt))

## Changelog

### 1.0.1

- **Outlook drag-and-drop** -- drag `.md` attachments directly from Outlook into the app window; virtual files are extracted and loaded automatically
- **Save As dialog for PDF export** -- PDF export now opens a Save dialog instead of silently writing next to the source file, making it easy to choose a different location (useful when the source is in a temp directory)
- Replaced tkinterdnd2 with a custom OLE drop target for broader drag-and-drop compatibility

### 1.0.0

- Initial release

## Contact

Robert Parks<br>
[raparks.com](https://raparks.com/)

## License

MIT -- free to use, modify, and distribute for any purpose (personal or commercial). See [LICENSE](LICENSE) for full text.
