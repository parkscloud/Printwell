# Releasing Printwell

Steps to create a new GitHub release with the installer attached.

## Prerequisites

- `build.bat` dependencies (Python 3.11+, PyInstaller)
- Inno Setup 6+ (`winget install JRSoftware.InnoSetup`)
- GitHub CLI (`winget install GitHub.cli`)

## Version bump

Update the version string in all three places:

1. `src/printwell/__init__.py` — `__version__`
2. `src/printwell/constants.py` — `APP_VERSION`
3. `installer.iss` — `AppVersion`

## Build the installer

```bash
# 1. Bundle the app with PyInstaller
build.bat

# 2. Compile the Windows installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `installer_output\PrintwellSetup.exe`

## Create the release

```bash
# Tag and create the release with the installer attached
gh release create vX.Y.Z installer_output/PrintwellSetup.exe --title "Printwell vX.Y.Z" --notes "Description of changes."
```

To generate notes from commits since the last release:

```bash
gh release create vX.Y.Z installer_output/PrintwellSetup.exe --title "Printwell vX.Y.Z" --generate-notes
```

## Verify

After creating the release, confirm:

1. The release appears at https://github.com/parkscloud/Printwell/releases
2. `PrintwellSetup.exe` is listed as a downloadable asset
3. The "Installed version" link in README.md resolves to the releases page
4. (Optional) Verify the installed build after a silent install:
   - `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{01969394-D605-4ACC-B3EA-D6BB89CD377D}_is1` → `DisplayVersion` matches the release
   - The startup shortcut `%ProgramData%\Microsoft\Windows\Start Menu\Programs\StartUp\Printwell.lnk` targets `Printwell.exe` with arguments `--minimized` (read via `WScript.Shell` → `CreateShortcut`)
   - Launching that shortcut starts Printwell tray-only (no visible window)

## Notes

- The version in `installer.iss` (`AppVersion=`) should match the release tag
- The version in `__init__.py` and `constants.py` should also match
- **Never change `AppId` in `installer.iss`** — it is the app's permanent identity in Windows' registry; changing it orphans every existing install (one-time migration already paid in v1.0.3)
- The uninstaller self-deletes asynchronously: when scripting uninstall → reinstall, poll for the uninstall registry key (and `Printwell.exe`) to disappear before running the new installer
- Silent upgrades keep the user's original task selections; a silent install after an uninstall applies all default tasks (startup, file association, desktop shortcut) — pass `/TASKS=""` to skip
- This file is tracked in the repo for portability
