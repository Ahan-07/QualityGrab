@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo QualityGrab Windows EXE Builder
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python from https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -m venv .venv
    if errorlevel 1 goto :failed
)

echo Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Building QualityGrab...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name QualityGrab --collect-all yt_dlp app.py
if errorlevel 1 goto :failed

echo.
echo Build complete.
echo Your app is here:
echo %CD%\dist\QualityGrab\QualityGrab.exe
echo.
echo IMPORTANT: FFmpeg must be installed and available on PATH for merging
echo separate video/audio streams and converting audio to MP3.
pause
exit /b 0

:failed
echo.
echo Build failed. Read the error above and check the README.
pause
exit /b 1
