import logging
import os
from typing import Any

from . import memory, speaker, stt, summarize

logger = logging.getLogger(__name__)


def process_audio(
    audio_path: str,
    received_at: str,
    *,
    db_path: str,
    samples_dir: str,
    style_prompts: dict[str, Any],
    speaker_override: str | None = None,
) -> dict[str, Any]:
    if speaker_override:
        speaker_name, conf = speaker_override, None
    else:
        speaker_name, conf = speaker.identify(audio_path, samples_dir)
    transcript = stt.transcribe(audio_path)

    try:
        summary, keywords = summarize.summarize(transcript, speaker_name, style_prompts)
    except Exception as e:
        logger.warning("Summarization failed: %s", e)
        summary = transcript.strip()[:280]
        keywords = ""

    file = os.path.basename(audio_path)
    memory.add_note(db_path, file, received_at, speaker_name, conf, transcript, summary, keywords)
    return memory.get_note(db_path, file)
