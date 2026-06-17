import logging
import os
import datetime
import yaml
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from .config import cfg
from . import pipeline, memory, speaker

logger = logging.getLogger(__name__)

SAMPLES_DIR = os.getenv("VOICE_SAMPLES_DIR", os.path.join(cfg.DATA_DIR, "voice_samples"))


def load_style_prompts(path: str = "prompts.yaml") -> dict:
    if os.path.exists(path):
        return yaml.safe_load(open(path, encoding="utf-8")) or {}
    else:
        return {"default": "Summarize the voice note concisely in 2-3 sentences, faithfully."}


STYLE_PROMPTS = load_style_prompts()


def _authorized(user_id: int) -> bool:
    return (not cfg.ALLOWED_USER_IDS) or (user_id in cfg.ALLOWED_USER_IDS)


async def on_voice(update, context):
    user = update.effective_user
    if not _authorized(user.id):
        return
    msg = update.message
    media = msg.voice or msg.audio
    if media is None:
        return
    tg_file = await context.bot.get_file(media.file_id)
    os.makedirs(cfg.MEDIA_DIR, exist_ok=True)
    path = os.path.join(cfg.MEDIA_DIR, f"{media.file_id}.ogg")
    await tg_file.download_to_drive(path)
    received_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    override = cfg.SENDER_NAMES.get(user.id)
    status = await msg.reply_text("Transcribing...")
    try:
        note = pipeline.process_audio(
            path, received_at, db_path=cfg.DB_PATH, samples_dir=SAMPLES_DIR,
            style_prompts=STYLE_PROMPTS, speaker_override=override,
        )
    except Exception as e:
        logger.exception("processing failed")
        await status.edit_text(f"Failed: {e}")
        return
    speaker = note.get("speaker") or "unknown"
    summary = note.get("summary") or ""
    kw = note.get("keywords") or ""
    reply = f"[{speaker}] {summary}"
    if kw:
        reply += f"\n\nKeywords: {kw}"
    await status.edit_text(reply)


async def cmd_recall(update, context):
    if not _authorized(update.effective_user.id):
        return
    query = " ".join(context.args).strip()
    notes = memory.find_notes(cfg.DB_PATH, query) if query else memory.recent(cfg.DB_PATH, 10)
    if not notes:
        await update.message.reply_text("No matching notes.")
        return
    lines = [f"- [{n.get('speaker')}] {(n.get('summary') or '')[:120]}  ({n.get('file')})" for n in notes]
    await update.message.reply_text("\n".join(lines))


async def cmd_correct(update, context):
    if not _authorized(update.effective_user.id):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /correct <what was wrong / the right version>")
        return
    recent = memory.recent(cfg.DB_PATH, 1)
    if not recent:
        await update.message.reply_text("No note to correct yet.")
        return
    updated = memory.correct_note(cfg.DB_PATH, recent[0]["file"], text, new_summary=text)
    await update.message.reply_text(f"Updated note for {updated['file']}.")


async def cmd_name(update, context):
    if not _authorized(update.effective_user.id):
        return
    label = " ".join(context.args).strip()
    if not label:
        await update.message.reply_text("Usage: /name <label>  (applies to your most recent voice note)")
        return
    recent = memory.recent(cfg.DB_PATH, 1)
    if not recent:
        await update.message.reply_text("No note to name yet.")
        return
    file = recent[0]["file"]
    path = os.path.join(cfg.MEDIA_DIR, file)
    enrolled = speaker.enroll(path, label, SAMPLES_DIR) if os.path.exists(path) else False
    memory.set_speaker(cfg.DB_PATH, file, label)
    if enrolled:
        await update.message.reply_text(f"Voice enrolled as '{label}' and note relabeled. Future notes from this voice map to {label}.")
    else:
        await update.message.reply_text(f"Note relabeled to '{label}'. (Voice not enrolled: audio missing or ffmpeg/resemblyzer unavailable.)")


async def cmd_relabel(update, context):
    if not _authorized(update.effective_user.id):
        return
    label = " ".join(context.args).strip()
    if not label:
        await update.message.reply_text("Usage: /relabel <label>")
        return
    recent = memory.recent(cfg.DB_PATH, 1)
    if not recent:
        await update.message.reply_text("No note to relabel yet.")
        return
    updated = memory.set_speaker(cfg.DB_PATH, recent[0]["file"], label)
    await update.message.reply_text(f"Relabeled note {updated['file']} to '{label}'.")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    memory.init_db(cfg.DB_PATH)
    if not cfg.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    app = ApplicationBuilder().token(cfg.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(CommandHandler("recall", cmd_recall))
    app.add_handler(CommandHandler("recent", cmd_recall))
    app.add_handler(CommandHandler("correct", cmd_correct))
    app.add_handler(CommandHandler("name", cmd_name))
    app.add_handler(CommandHandler("relabel", cmd_relabel))
    print("voice-note-digest bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()