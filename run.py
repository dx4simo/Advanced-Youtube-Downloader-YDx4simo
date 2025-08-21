#.===============================================================
#. --- YOUTUBE DOWNLOADER V1.0 ---
#. --- CREATED BY : ISLAM ALBADAWY ---
#. --- NOTE: ASCII-only icons for maximum terminal compatibility ---
#.===============================================================

import os
import sys
import shutil
import zipfile
import platform
import subprocess
import urllib.request
import tarfile

# -------------------------
# ASCII Icons (CMD-safe)
# -------------------------
ICON = {
    "url":   "[URL]",
    "ok":    "[OK]",
    "err":   "[ERR]",
    "warn":  "[!]",
    "dl":    "[DL]",
    "tip":   "[TIP]",
    "prompt": ">"
}

# -------------------------
# Auto-install required packages (yt-dlp, colorama, pyfiglet)
# -------------------------
def ensure_pip_package(pkg: str, import_name: str = None, upgrade: bool = False):
    """
    Ensure a pip package is installed. If missing, install it.
    - pkg: pip package name
    - import_name: module name to import (defaults to pkg)
    - upgrade: if True, attempt to upgrade
    """
    import importlib
    modname = import_name or pkg
    try:
        importlib.import_module(modname)
        return True
    except ImportError:
        pass

    print(f"{ICON['tip']} Installing '{pkg}' ...")
    args = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        args.append("-U")
    args.append(pkg)
    try:
        subprocess.run(args, check=True)
    except Exception as e:
        print(f"{ICON['err']} Failed to install {pkg}: {e}")
        return False

    try:
        importlib.import_module(modname)
        return True
    except ImportError:
        print(f"{ICON['err']} Could not import {modname} after installation.")
        return False

# Make sure required packages exist (yt-dlp upgrade recommended)
ensure_pip_package("yt-dlp", "yt_dlp", upgrade=True)
# Optional but nice-to-have for banner
ensure_pip_package("colorama", "colorama", upgrade=False)
ensure_pip_package("pyfiglet", "pyfiglet", upgrade=False)

# Now safe to import
from yt_dlp import YoutubeDL
try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
except Exception:
    class _Dummy:
        RESET_ALL = ''
        RED = YELLOW = GREEN = CYAN = MAGENTA = BLUE = WHITE = ''
        BRIGHT = NORMAL = DIM = ''
    Fore = _Dummy()
    Style = _Dummy()

# ---------------------------------
# Change CWD to script directory
# ---------------------------------
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------
# Helpers: progress bar (ASCII-first, auto-fallback)
# ---------------------------------
USE_ASCII = os.environ.get("ASCII", "0") == "1" or os.environ.get("NO_UNICODE", "0") == "1"

def _charset():
    """Choose characters for progress bar (Unicode blocks if supported, else ASCII)."""
    if USE_ASCII:
        return "#", "-"
    try:
        # Try encoding a block character with current stdout encoding
        ("█").encode(sys.stdout.encoding or "utf-8")
        return "█", "·"  # Unicode full & dot
    except Exception:
        return "#", "-"  # ASCII fallback

FULL_CH, EMPTY_CH = _charset()

def _bar(percent: float, width: int = 30) -> str:
    """Return a simple progress bar string using chosen charset."""
    p = max(0.0, min(100.0, percent))
    filled = int(width * p / 100.0)
    return f"[{FULL_CH*filled}{EMPTY_CH*(width-filled)}] {p:5.1f}%"

def _reporthook_builder(label: str):
    """Build a reporthook for urlretrieve to show progress (for ffmpeg download)."""
    last_percent = -1
    def _hook(block_count, block_size, total_size):
        nonlocal last_percent
        downloaded = block_count * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            if int(percent) != int(last_percent):
                last_percent = percent
                print(f"\r{label} {_bar(percent)}", end="", flush=True)
            if downloaded >= total_size:
                print(f"\r{label} {_bar(100.0)}", flush=True)
        else:
            mb = downloaded / (1024*1024)
            print(f"\r{label} {mb:.1f} MB...", end="", flush=True)
    return _hook

# ---------------------------------
# Banner
# ---------------------------------
def print_banner():
    """Pretty colored banner at start (ASCII-only text)."""
    import shutil as _shutil
    cols = max(60, _shutil.get_terminal_size((100, 20)).columns)
    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.MAGENTA, Fore.BLUE]
    try:
        from pyfiglet import Figlet
        f1 = Figlet(font="slant")
        f2 = Figlet(font="standard")
        text1 = f1.renderText("YOUTUBE DOWNLOADER")
        text2 = f2.renderText("V1.0")
        lines = (text1 + text2).splitlines()
    except Exception:
        # Fallback ASCII banner
        lines = r"""
__     __  _   _ _   _ _____ _____ _   _ _____ ____   ____   ____  _   _ _   _ _   _ ____  _____ ____  
\ \   / / | | | | \ | |_   _| ____| \ | | ____|  _ \ |  _ \ / __ \| \ | | \ | | \ | |  _ \| ____|  _ \ 
 \ \ / /  | | | |  \| | | | |  _| |  \| |  _| | | | || | | | |  | |  \| |  \| |  \| | | | |  _| | |_) |
  \ V /   | |_| | |\  | | | | |___| |\  | |___| |_| || |_| | |__| | |\  | |\  | |\  | |_| | |___|  _ < 
   \_/     \___/ |_| \_| |_| |_____|_| \_|_____|____/ |____/ \____/|_| \_|_| \_|_| \_|____/|_____|_| \_|
""".splitlines()
    print()
    for i, line in enumerate(lines):
        c = colors[i % len(colors)]
        print(c + Style.BRIGHT + line.center(cols) + Style.RESET_ALL)
    print()

# ---------------------------------
# Paths & folders
# ---------------------------------
def get_script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))

def get_save_folder() -> str:
    """Ensure a 'Videos' folder exists next to this script."""
    save_path = os.path.join(get_script_dir(), "Videos")
    os.makedirs(save_path, exist_ok=True)
    return save_path

def ffmpeg_path() -> str:
    """Return path to local ffmpeg binary inside script folder."""
    if platform.system().lower() == "windows":
        return os.path.join(get_script_dir(), "ffmpeg", "ffmpeg.exe")
    else:
        return os.path.join(get_script_dir(), "ffmpeg", "ffmpeg")

# ---------------------------------
# FFmpeg management (with progress)
# ---------------------------------
def check_ffmpeg() -> str:
    """
    Check if ffmpeg is available. If not, download a portable/static build
    into ./ffmpeg next to the script and return its path.
    """
    # 1) Try system ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return "ffmpeg"  # Use system ffmpeg
    except Exception:
        pass

    # 2) Try local ffmpeg
    local_ff = ffmpeg_path()
    if os.path.exists(local_ff):
        return local_ff

    # 3) Download portable ffmpeg (with progress)
    print(f"{ICON['warn']} ffmpeg not found. Downloading a portable version...")

    ffmpeg_dir = os.path.join(get_script_dir(), "ffmpeg")
    os.makedirs(ffmpeg_dir, exist_ok=True)

    system_name = platform.system().lower()
    if system_name == "windows":
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = os.path.join(ffmpeg_dir, "ffmpeg.zip")
        urllib.request.urlretrieve(url, zip_path, _reporthook_builder(f"{ICON['dl']} Downloading ffmpeg (Windows)"))
        print(" - Extracting...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        os.remove(zip_path)

        moved = False
        for root, _, files in os.walk(ffmpeg_dir):
            if "ffmpeg.exe" in files:
                src = os.path.join(root, "ffmpeg.exe")
                dst = os.path.join(ffmpeg_dir, "ffmpeg.exe")
                if src != dst:
                    shutil.move(src, dst)
                moved = True
                break
        if not moved:
            raise RuntimeError("Could not locate ffmpeg.exe inside the downloaded archive.")
        return os.path.join(ffmpeg_dir, "ffmpeg.exe")
    else:
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tar_path = os.path.join(ffmpeg_dir, "ffmpeg.tar.xz")
        urllib.request.urlretrieve(url, tar_path, _reporthook_builder(f"{ICON['dl']} Downloading ffmpeg (Unix)"))
        print(" - Extracting...")
        with tarfile.open(tar_path, "r:xz") as tar_ref:
            tar_ref.extractall(ffmpeg_dir)
        os.remove(tar_path)

        moved = False
        for root, _, files in os.walk(ffmpeg_dir):
            if "ffmpeg" in files and not root.endswith("doc"):
                src = os.path.join(root, "ffmpeg")
                dst = os.path.join(ffmpeg_dir, "ffmpeg")
                if src != dst:
                    shutil.move(src, dst)
                try:
                    os.chmod(dst, 0o755)
                except Exception:
                    pass
                moved = True
                break
        if not moved:
            raise RuntimeError("Could not locate ffmpeg binary inside the downloaded archive.")
        return os.path.join(ffmpeg_dir, "ffmpeg")

# ---------------------------------
# yt-dlp format selector
# ---------------------------------
def build_format_selector(choice: str) -> str:
    """
    Map menu choice to yt-dlp format selector:
    Prefer best video <= requested height + best audio, otherwise fallback to best single stream <= height.
    """
    mapping = {"1": 360, "2": 480, "3": 720, "4": 1080}
    if choice in mapping:
        h = mapping[choice]
        return f"bv*[height<={h}]+ba/b[height<={h}]"
    elif choice in {"5", "7", "8"}:  # Best or Subtitle modes use best available
        return "bv*+ba/best"
    elif choice == "6":  # Audio only
        return "bestaudio/best"
    else:
        return "bv*[height<=720]+ba/b[height<=720]"

# ---------------------------------
# yt-dlp progress hook (video/audio)
# ---------------------------------
def progress_hook(d):
    status = d.get('status')
    if status == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        downloaded = d.get('downloaded_bytes') or 0
        if total > 0:
            percent = downloaded * 100.0 / total
            bar = _bar(percent)
        else:
            bar = "[Downloading...]"
        sp = (d.get('_speed_str') or '').strip()
        eta = d.get('eta')
        eta_str = f" | ETA: {eta}s" if eta is not None else ""
        print(f"\r{ICON['dl']} {bar} | {sp or '-'}{eta_str}", end="", flush=True)
    elif status == 'finished':
        print(f"\n{ICON['ok']} Downloaded. Post-processing...")

# ---------------------------------
# Main
# ---------------------------------
def main():
    print_banner()  # Banner at start

    url = input(f"{ICON['url']} Enter video or playlist URL: ").strip()

    print("\nSelect quality/mode:")
    print("1 - 360p")
    print("2 - 480p")
    print("3 - 720p (common)")
    print("4 - 1080p (requires ffmpeg to merge A/V)")
    print("5 - Best Available")
    print("6 - Audio Only (MP3)")
    print("7 - Video + Subtitles (save .srt AND embed soft subs)")
    print("8 - Video + Hard-burn Subtitles (save .srt AND burn into video)")
    choice = input(f"{ICON['prompt']} Your choice: ").strip()

    save_path = get_save_folder()
    fmt = build_format_selector(choice)

    # Ensure ffmpeg is available (merging/embedding/burning & recoding to MP4)
    ffmpeg_bin = check_ffmpeg()
    print(f"\nUsing ffmpeg: {ffmpeg_bin}")

    # Base yt-dlp options
    ydl_opts = {
        "outtmpl": os.path.join(save_path, "%(title)s.%(ext)s"),
        "format": fmt,
        "noplaylist": False,
        "ignoreerrors": True,
        "progress_hooks": [progress_hook],
        "windowsfilenames": True,
        "merge_output_format": "mp4",      # merge container target
        "ffmpeg_location": os.path.dirname(ffmpeg_bin),
        "quiet": False,
        "consoletitle": False,
    }

    # Guarantee MP4 output (skip for MP3 and hard-burn which already converts)
    if choice not in {"6", "8"}:
        ydl_opts["recodevideo"] = "mp4"

    # Audio-only (MP3)
    if choice == "6":
        ydl_opts.update({
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        })

    # Soft subtitles
    if choice == "7":
        langs_in = input("Enter subtitle language codes (comma-separated, e.g., en,ar,de). Default: en: ").strip()
        langs = [x.strip() for x in langs_in.split(",") if x.strip()] or ["en"]
        ydl_opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": langs,
            "subtitlesformat": "srt",
            "embedsubtitles": True,
        })

    # Hard-burn subtitles (re-encode to MP4 with burn)
    if choice == "8":
        langs_in = input("Enter subtitle language codes (comma-separated, e.g., en,ar,de). Default: en: ").strip()
        langs = [x.strip() for x in langs_in.split(",") if x.strip()] or ["en"]
        ydl_opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": langs,
            "subtitlesformat": "srt",
            "postprocessors": [
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
            ],
            "postprocessor_args": {
                "FFmpegVideoConvertor": [
                    "-vf", "subtitles=%(subtitle_filename)s"
                ]
            },
        })

    print(f"\nSave folder: {save_path}")
    print(f"Format selector: {fmt}\n")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"\n{ICON['ok']} Done!")
        if choice == "8":
            print(f"{ICON['ok']} Subtitles were hard-burned into the video (cannot be toggled off).")
        elif choice == "7":
            print(f"{ICON['ok']} Subtitles were embedded as a soft track and also saved as .srt.")
        elif choice in {"1","2","3","4","5"}:
            print(f"{ICON['ok']} Final output is MP4.")
    except Exception as e:
        print(f"\n{ICON['err']} Error during download/conversion:")
        print(str(e))
        print("\nTips:")
        print("- Ensure internet is available for first-time auto-setup.")
        print("- Update yt-dlp: pip install -U yt-dlp (script tries to auto-upgrade).")
        print("- For hard-burn (8), make sure requested subtitle languages exist.")
        print("- On Windows, if paths with spaces cause issues, move the script to a simple path (e.g., C:\\yt).")
        sys.exit(1)

if __name__ == "__main__":
    main()
