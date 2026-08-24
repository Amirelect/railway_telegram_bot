import os
import re
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from downloader import (
    get_video_info,
    download_video,
    delete_file,
)


MAX_FILE_SIZE = 50 * 1024 * 1024


YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=[\w-]+"
    r"|youtu\.be/[\w-]+"
    r"|youtube\.com/shorts/[\w-]+)",
    re.IGNORECASE,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "سلام 👋\n"
        "ربات با موفقیت فعال شد.\n\n"
        "🎬 لینک YouTube را برای من ارسال کنید."
    )


def is_youtube_url(text: str) -> bool:
    return bool(YOUTUBE_REGEX.search(text))


def format_duration(seconds):
    if not seconds:
        return "نامشخص"

    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def format_size(size):
    if not size:
        return "نامشخص"

    size = float(size)

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"

    return f"{size / (1024 * 1024):.1f} MB"


async def handle_youtube(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message

    url = message.text.strip()

    if not is_youtube_url(url):
        await message.reply_text(
            "❌ این لینک به نظر نمی‌رسد لینک معتبر YouTube باشد."
        )
        return

    status_message = await message.reply_text(
        "🔎 در حال بررسی ویدیو..."
    )
    
    loop = asyncio.get_running_loop()

    try:
        # Get video information.
        info = await asyncio.to_thread(
            get_video_info,
            url
        )

        title = info.get("title", "بدون عنوان")
        duration = format_duration(
            info.get("duration")
        )

        await status_message.edit_text(
            f"🎬 {title}\n"
            f"⏱ مدت: {duration}\n\n"
            "⬇️ در حال دانلود..."
        )

        last_progress = {"value": -1}

        async def update_progress(percent):
            current = int(percent)

            # Only update Telegram when percentage changes.
            if current == last_progress["value"]:
                return

            last_progress["value"] = current

            try:
                await status_message.edit_text(
                    f"🎬 {title}\n"
                    f"⏱ مدت: {duration}\n\n"
                    f"⬇️ در حال دانلود...\n"
                    f"📊 پیشرفت: {current}%"
                )
            except Exception:
                pass

        def progress_hook(data):
            if data["status"] != "downloading":
                return

            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
            )

            downloaded = data.get(
                "downloaded_bytes",
                0
            )

            if total:
                percent = (
                    downloaded / total
                ) * 100

                asyncio.run_coroutine_threadsafe(
                    update_progress(percent),
                    loop
                )

        # Download video.
        filepath, info = await asyncio.to_thread(
            download_video,
            url,
            progress_hook
        )

        if not filepath or not os.path.exists(filepath):
            raise RuntimeError(
                "فایل دانلود شده پیدا نشد."
            )

        file_size = os.path.getsize(filepath)

        if file_size > MAX_FILE_SIZE:
            delete_file(filepath)

            await status_message.edit_text(
                f"❌ حجم ویدیو زیاد است.\n\n"
                f"📦 حجم فایل: {format_size(file_size)}\n"
                f"📏 حداکثر مجاز: 50 MB\n\n"
                "در مرحله بعد قابلیت انتخاب کیفیت "
                "را اضافه می‌کنیم."
            )

            return

        await status_message.edit_text(
            f"📤 دانلود کامل شد.\n"
            f"📦 حجم: {format_size(file_size)}\n\n"
            "در حال ارسال به Telegram..."
        )

        # Send video.
        with open(filepath, "rb") as video_file:
            await message.reply_video(
                video=video_file,
                caption=(
                    f"🎬 {title}\n"
                    f"⏱ {duration}"
                ),
                supports_streaming=True,
            )

        await status_message.delete()

        # Delete temporary file.
        delete_file(filepath)

    except Exception as error:

        print(
            f"Download error: {type(error).__name__}: {error}"
        )

        await status_message.edit_text(
            "❌ متأسفانه دانلود ویدیو انجام نشد.\n\n"
            "ممکن است YouTube دسترسی به این ویدیو را "
            "محدود کرده باشد یا لینک معتبر نباشد."
        )


async def echo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text.strip()

    if is_youtube_url(text):
        await handle_youtube(
            update,
            context
        )
        return

    await update.message.reply_text(
        f"شما گفتید:\n{text}"
    )


def main():

    token = os.environ["TELEGRAM_TOKEN"]

    app = (
        ApplicationBuilder()
        .token(token)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            echo
        )
    )

    print("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()