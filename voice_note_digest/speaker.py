import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def identify(audio_path: str, samples_dir: str, threshold: float = 0.75) -> tuple[str, float | None]:
    try:
        import numpy as np
        from resemblyzer import VoiceEncoder, preprocess_wav
    except ImportError:
        return ("unknown", None)

    if not os.path.isdir(samples_dir):
        return ("unknown", None)

    try:
        input_wav = None
        try:
            suffix = Path(audio_path).suffix.lower()
            if suffix in ('.ogg', '.opus', '.mp3', '.m4a', '.webm'):
                input_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                subprocess.run(
                    ['ffmpeg', '-i', audio_path, '-ac', '1', '-ar', '16000', input_wav.name],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                input_wav.flush()
                audio_path = input_wav.name

            encoder = VoiceEncoder()
            input_embed = encoder.embed_utterance(preprocess_wav(audio_path))

            best_label = "unknown"
            best_score: float | None = None

            for speaker_dir in os.listdir(samples_dir):
                sample_path = os.path.join(samples_dir, speaker_dir, 'sample.wav')
                embed_path = os.path.join(samples_dir, speaker_dir, 'embedding.npy')

                if not os.path.isfile(sample_path):
                    continue

                if os.path.isfile(embed_path):
                    ref_embed = np.load(embed_path)
                else:
                    ref_embed = encoder.embed_utterance(preprocess_wav(sample_path))
                    np.save(embed_path, ref_embed)

                score = float(np.dot(input_embed, ref_embed) / (np.linalg.norm(input_embed) * np.linalg.norm(ref_embed)))

                if best_score is None or score > best_score:
                    best_score = score
                    best_label = speaker_dir

            if best_score is None:
                return ("unknown", None)

            if best_score < threshold:
                return ("unknown", round(best_score, 3))
            return (best_label, round(best_score, 3))

        finally:
            if input_wav is not None:
                try:
                    os.unlink(input_wav.name)
                except OSError:
                    pass

    except Exception as e:
        logger.warning("Speaker identification failed: %s", e)
        return ("unknown", None)


def enroll(audio_path: str, label: str, samples_dir: str) -> bool:
    dest_dir = os.path.join(samples_dir, label)
    os.makedirs(dest_dir, exist_ok=True)
    dest_wav = os.path.join(dest_dir, 'sample.wav')
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', audio_path, '-ac', '1', '-ar', '16000', dest_wav],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        embed_cache = os.path.join(dest_dir, 'embedding.npy')
        if os.path.isfile(embed_cache):
            os.remove(embed_cache)
        return True
    except Exception as e:
        logger.warning("Speaker enrollment failed: %s", e)
        return False
