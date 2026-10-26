# QualityGrab — Windows 11 package

QualityGrab is a small Tkinter desktop GUI using yt-dlp. Use it only for videos you own, have permission to download, or are otherwise authorized to save. Respect copyright and the platform's terms.

## Features
- Single video and playlist downloads
- Best available video + audio (4K/8K if offered by the source)
- Optional 1080p and 4K caps
- Audio-only MP3 conversion
- Playlist subfolders and numbered filenames
- Progress, activity log, cancel request
- Default output folder: the current user's `Downloads` folder
- Concurrent fragment downloads where supported by the source

## Requirements
- Windows 10/11, 64-bit recommended
- Python 3.11+ from https://www.python.org/downloads/windows/
- FFmpeg installed and available on PATH for merging separate streams and MP3 conversion

Official project pages:
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- FFmpeg: https://ffmpeg.org/download.html
- PyInstaller: https://pyinstaller.org/

## Run from source
1. Extract this folder.
2. Open PowerShell in this folder.
3. Run:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

4. Install FFmpeg if needed. Open a new terminal and check `ffmpeg -version`.

## Build the Windows app
1. Double-click `build_windows.bat`.
2. Wait for the dependencies to install and PyInstaller to finish.
3. The application will be placed at:

   `dist\QualityGrab\QualityGrab.exe`

4. Copy the entire `dist\QualityGrab` folder to the PC where you want to run it. Do not copy only the EXE; the folder contains runtime files.

FFmpeg is not bundled in this package. Install it separately and make sure `ffmpeg.exe` and `ffprobe.exe` are available on PATH. A future packaging pass can bundle verified FFmpeg binaries if desired.

## Quality and speed notes
- Best available has no resolution cap; 4K/8K are only possible if offered by the source.
- Fragment concurrency can improve throughput for compatible fragmented streams, but no setting can guarantee maximum speed. Network capacity and source-side limits apply.
- Audio-only mode converts to MP3, which is lossy.
- This starter app shows progress for the current item, not a total playlist-wide percentage.


## Automated Windows EXE build with GitHub Actions

This package includes `.github/workflows/build-windows.yml`. It builds the app on a Windows GitHub-hosted runner and uploads a portable folder artifact with `QualityGrab.exe`, `ffmpeg.exe`, and `ffprobe.exe`.

### How to get the built EXE package
1. Create a GitHub repository for this project (or use a repository you own).
2. Upload/push the **contents** of this folder to the repository root, including the hidden `.github` folder.
3. Ensure the default branch is named `main` or `master`.
4. Open the repository's **Actions** tab.
5. Select **Build QualityGrab for Windows** and click **Run workflow** (or push a change to `app.py`).
6. When the run completes successfully, open the run and download the artifact named **QualityGrab-Windows-x64**.
7. Extract the downloaded artifact ZIP. Run `QualityGrab.exe` and keep all files in the extracted folder together.

GitHub Actions requires a GitHub account and Actions must be enabled for the repository. The artifact is temporary (14-day retention) and is not a public Release. You can later add a release workflow if you want a permanent versioned download.

The workflow downloads a Windows FFmpeg build from Gyan.dev, a Windows build provider linked from FFmpeg's official download page. Review that provider's licensing and distribution terms before redistributing the package publicly.
