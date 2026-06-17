import logging
import os
import time
from .config import cfg


def purge(media_dir: str = None, days: int = None) -> int:
    if media_dir is None:
        media_dir = cfg.MEDIA_DIR
    if days is None:
        days = cfg.RETENTION_DAYS

    now = time.time()
    cutoff = now - days * 86400
    suffixes = {'.ogg', '.opus', '.mp3', '.m4a', '.webm'}
    deleted = 0

    for filename in os.listdir(media_dir):
        filepath = os.path.join(media_dir, filename)
        if os.path.isfile(filepath) and any(filename.endswith(s) for s in suffixes):
            try:
                st = os.stat(filepath)
                if st.st_mtime < cutoff:
                    os.remove(filepath)
                    logging.info(f"deleted {filepath}")
                    deleted += 1
            except OSError:
                pass

    return deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"deleted {purge()} files")
