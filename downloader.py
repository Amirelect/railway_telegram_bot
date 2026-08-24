import os
import yt_dlp


DOWNLOAD_DIR = "/tmp/telegram_youtube"


def ensure_download_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_video_info(url: str):
    """
    Get YouTube video information without downloading the video.
    """

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return info


def download_video(url: str, progress_hook=None):
    """
    Download a YouTube video.

    Returns:
        tuple[str, dict]:
            downloaded file path and video information
    """

    ensure_download_dir()

    output_template = os.path.join(
        DOWNLOAD_DIR,
        "%(id)s.%(ext)s"
    )

    ydl_opts = {
        "outtmpl": output_template,

        "noplaylist": True,

        # Prefer MP4 video + M4A audio.
        # Limit height to 720p for a reasonable Telegram file size.
        "format": (
            "bestvideo[height<=720][ext=mp4]+"
            "bestaudio[ext=m4a]/"
            "best[height<=720][ext=mp4]/"
            "best[height<=720]"
        ),

        # Merge video/audio into MP4.
        "merge_output_format": "mp4",

        "quiet": True,
        "no_warnings": True,

        "progress_hooks": (
            [progress_hook]
            if progress_hook
            else []
        ),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            url,
            download=True
        )

        filename = ydl.prepare_filename(info)

        # After merging, yt-dlp may change the extension.
        merged_filename = os.path.splitext(filename)[0] + ".mp4"

        if os.path.exists(merged_filename):
            filename = merged_filename

    return filename, info


def delete_file(filepath: str):
    """
    Delete downloaded temporary file.
    """

    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError:
            pass