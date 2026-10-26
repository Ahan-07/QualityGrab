import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import yt_dlp

# When packaged as an EXE, prefer bundled FFmpeg tools next to the executable.
if getattr(sys, "frozen", False):
    _app_dir = Path(sys.executable).resolve().parent
    os.environ["PATH"] = str(_app_dir) + os.pathsep + os.environ.get("PATH", "")

APP_NAME = "QualityGrab"
# Default to the current Windows user's Downloads folder.
DEFAULT_FOLDER = Path.home() / "Downloads"


class QueueLogger:
    """Send yt-dlp messages safely to the GUI thread."""
    def __init__(self, events):
        self.events = events

    def debug(self, message):
        if message and message.strip():
            self.events.put(("log", message))

    def warning(self, message):
        self.events.put(("log", "WARNING: " + message))

    def error(self, message):
        self.events.put(("log", "ERROR: " + message))


class QualityGrabApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("790x650")
        self.root.minsize(650, 540)

        self.events = queue.Queue()
        self.worker = None
        self.cancel_event = threading.Event()
        self.closing = False

        DEFAULT_FOLDER.mkdir(parents=True, exist_ok=True)

        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=str(DEFAULT_FOLDER))
        self.mode_var = tk.StringVar(value="Video")
        self.quality_var = tk.StringVar(value="Best available")
        self.playlist_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")

        self.build_ui()
        self.root.after(100, self.process_events)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer, text="QualityGrab",
            font=("Segoe UI", 23, "bold")
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text="Video • Playlists • Audio • Best available quality"
        ).pack(anchor="w", pady=(0, 16))

        ttk.Label(outer, text="Video or playlist URL").pack(anchor="w")

        url_row = ttk.Frame(outer)
        url_row.pack(fill="x", pady=(5, 12))

        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(
            url_row, text="Paste", command=self.paste_url
        ).pack(side="left", padx=(8, 0))

        ttk.Label(outer, text="Save location").pack(anchor="w")

        folder_row = ttk.Frame(outer)
        folder_row.pack(fill="x", pady=(5, 12))

        ttk.Entry(folder_row, textvariable=self.folder_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            folder_row, text="Browse...", command=self.choose_folder
        ).pack(side="left", padx=(8, 0))

        settings = ttk.Frame(outer)
        settings.pack(fill="x", pady=(0, 8))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Download type").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(settings, text="Quality").grid(
            row=0, column=1, sticky="w", padx=(18, 0)
        )

        self.mode_box = ttk.Combobox(
            settings, textvariable=self.mode_var,
            values=["Video", "Audio only"],
            state="readonly", width=18
        )
        self.mode_box.grid(row=1, column=0, sticky="w", pady=5)

        self.quality_box = ttk.Combobox(
            settings, textvariable=self.quality_var,
            values=["Best available", "Up to 1080p", "Up to 4K"],
            state="readonly", width=24
        )
        self.quality_box.grid(
            row=1, column=1, sticky="w", padx=(18, 0), pady=5
        )

        ttk.Checkbutton(
            outer,
            text="Download entire playlist when the URL contains one",
            variable=self.playlist_var
        ).pack(anchor="w", pady=(0, 12))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(0, 12))

        self.download_button = ttk.Button(
            buttons, text="Start download", command=self.start_download
        )
        self.download_button.pack(side="left", fill="x", expand=True)

        self.cancel_button = ttk.Button(
            buttons, text="Cancel", command=self.cancel_download,
            state="disabled"
        )
        self.cancel_button.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(
            outer, mode="determinate", maximum=100
        )
        self.progress.pack(fill="x")

        ttk.Label(outer, textvariable=self.status_var).pack(
            anchor="w", pady=(6, 10)
        )
        ttk.Label(outer, text="Activity log").pack(anchor="w")

        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True, pady=(5, 0))

        self.log = tk.Text(
            log_frame, height=12, wrap="word",
            state="disabled", font=("Consolas", 9)
        )
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.mode_box.bind(
            "<<ComboboxSelected>>", self.update_quality_options
        )
        self.update_quality_options()

    def update_quality_options(self, _event=None):
        self.quality_box.configure(
            state="disabled" if self.mode_var.get() == "Audio only"
            else "readonly"
        )

    def write_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", str(message) + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def paste_url(self):
        try:
            self.url_var.set(self.root.clipboard_get().strip())
        except tk.TclError:
            messagebox.showwarning(
                "Clipboard empty", "Copy a video or playlist URL first."
            )

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def start_download(self):
        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()

        if not url.startswith(("https://", "http://")):
            messagebox.showerror(
                "Invalid URL", "Paste a valid video or playlist URL."
            )
            return
        if not folder:
            messagebox.showerror(
                "Missing folder", "Choose a save location."
            )
            return
        if self.worker and self.worker.is_alive():
            return

        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Folder error", str(exc))
            return

        self.cancel_event.clear()
        self.progress["value"] = 0
        self.status_var.set("Preparing download...")
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.write_log("=" * 45)
        self.write_log("Preparing download...")

        args = (
            url, folder, self.mode_var.get(),
            self.quality_var.get(), self.playlist_var.get()
        )
        self.worker = threading.Thread(
            target=self.download_worker, args=args, daemon=True
        )
        self.worker.start()

    def download_worker(self, url, folder, mode, quality, download_playlist):
        def progress_hook(data):
            if self.cancel_event.is_set():
                raise yt_dlp.utils.DownloadError(
                    "Cancellation requested by user."
                )

            info = data.get("info_dict") or {}
            index = info.get("playlist_index")
            count = info.get("n_entries") or info.get("playlist_count")
            prefix = ""
            if index:
                prefix = f"Item {index}"
                if count:
                    prefix += f"/{count}"
                prefix += " | "

            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent = min(100, downloaded * 100 / total) if total else 0
                speed = data.get("_speed_str", "")
                eta = data.get("_eta_str", "")
                filename = os.path.basename(data.get("filename", ""))

                self.events.put((
                    "progress", percent,
                    f"{prefix}{percent:.1f}% | {speed} | ETA {eta}"
                ))
                if filename:
                    self.events.put(("file", filename))
            elif data.get("status") == "finished":
                self.events.put((
                    "progress", 100,
                    f"{prefix}Download received; processing/merging..."
                ))

        if mode == "Audio only":
            options = {
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0"
                }]
            }
        else:
            if quality == "Up to 1080p":
                fmt = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            elif quality == "Up to 4K":
                fmt = "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best"
            else:
                fmt = "bestvideo+bestaudio/best"

            options = {
                "format": fmt,
                "merge_output_format": "mkv"
            }

        if download_playlist:
            output_template = os.path.join(
                folder, "%(playlist_title)s",
                "%(playlist_index)03d - %(title).180B [%(id)s].%(ext)s"
            )
        else:
            output_template = os.path.join(
                folder, "%(title).180B [%(id)s].%(ext)s"
            )

        options.update({
            "outtmpl": output_template,
            "noplaylist": not download_playlist,
            "windowsfilenames": True,
            "continuedl": True,
            # Parallel fragment downloading where the source supports it.
            "concurrent_fragment_downloads": 8,
            "retries": 10,
            "fragment_retries": 10,
            "file_access_retries": 3,
            "socket_timeout": 30,
            "progress_hooks": [progress_hook],
            "logger": QueueLogger(self.events),
            "quiet": True,
            "no_warnings": False,
            "ignoreerrors": False,
        })

        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.download([url])
            if self.cancel_event.is_set():
                self.events.put(("cancelled",))
            else:
                self.events.put(("success", folder))
        except Exception as exc:
            if self.cancel_event.is_set():
                self.events.put(("cancelled",))
            else:
                self.events.put(("error", str(exc)))

    def cancel_download(self):
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_var.set("Cancellation requested...")
        self.write_log("Cancellation requested.")

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "progress":
                    _, percent, status = event
                    self.progress["value"] = percent
                    self.status_var.set(status)
                elif kind == "file":
                    self.status_var.set("Downloading: " + event[1])
                elif kind == "log":
                    self.write_log(event[1])
                elif kind == "success":
                    self.progress["value"] = 100
                    self.status_var.set("Completed")
                    self.write_log("Finished. Saved in: " + event[1])
                    self.set_idle()
                    if not self.closing:
                        messagebox.showinfo(
                            "Download complete",
                            "Finished successfully.\n\nSaved in:\n" + event[1]
                        )
                elif kind == "error":
                    self.status_var.set("Download failed")
                    self.write_log("ERROR: " + event[1])
                    self.set_idle()
                    if not self.closing:
                        messagebox.showerror("Download error", event[1])
                elif kind == "cancelled":
                    self.status_var.set("Cancelled")
                    self.write_log("Download cancelled.")
                    self.set_idle()
        except queue.Empty:
            pass

        if not self.closing:
            self.root.after(100, self.process_events)

    def set_idle(self):
        self.download_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.worker = None

    def close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(
                "Exit", "A download is running. Request cancellation and exit?"
            ):
                return
            self.cancel_event.set()
        self.closing = True
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = QualityGrabApp(root)
    root.mainloop()
