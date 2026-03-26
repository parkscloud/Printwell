@echo off
REM Build Printwell with PyInstaller (onedir mode)
REM Run from the project root: build.bat

echo Building Printwell...

pyinstaller --noconfirm Printwell.spec

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build succeeded! Output in dist\Printwell\
) else (
    echo Build FAILED.
)
