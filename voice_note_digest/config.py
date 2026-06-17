import os
from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class Config:
    TELEGRAM_BOT_TOKEN: str = None
    STT_PROVIDER: str = "openai"
    STT_API_KEY: str = ""
    STT_MODEL: str = "whisper-1"
    LLM_PROVIDER: str = "mistral"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "mistral-large-latest"
    LLM_BASE_URL: str = "https://api.mistral.ai/v1"
    DATA_DIR: str = "./data"
    MEDIA_DIR: str = "./data/inbound"
    DB_PATH: str = "./data/memory.db"
    RETENTION_DAYS: int = 90
    ALLOWED_USER_IDS: Set[int] = field(default_factory=set)
    # Telegram sender id -> fixed name. Overrides voice biometrics for that sender.
    SENDER_NAMES: Dict[int, str] = field(default_factory=dict)

    def __getattribute__(self, name):
        if name == "TELEGRAM_BOT_TOKEN":
            val = object.__getattribute__(self, name)
            if val is None:
                raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")
            return val
        return object.__getattribute__(self, name)


def _parse_allowed_user_ids(env_value: str) -> Set[int]:
    if not env_value:
        return set()
    try:
        return {int(x.strip()) for x in env_value.split(",") if x.strip()}
    except ValueError:
        return set()


def _parse_sender_names(env_value: str) -> Dict[int, str]:
    """Parse 'id:Name,id:Name' into {id: Name}."""
    result: Dict[int, str] = {}
    if not env_value:
        return result
    for pair in env_value.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        sid, name = pair.split(":", 1)
        try:
            result[int(sid.strip())] = name.strip()
        except ValueError:
            continue
    return result


def _load() -> Config:
    return Config(
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"),
        STT_PROVIDER=os.getenv("STT_PROVIDER", "openai"),
        STT_API_KEY=os.getenv("STT_API_KEY", ""),
        STT_MODEL=os.getenv("STT_MODEL", "whisper-1"),
        LLM_PROVIDER=os.getenv("LLM_PROVIDER", "mistral"),
        LLM_API_KEY=os.getenv("LLM_API_KEY", ""),
        LLM_MODEL=os.getenv("LLM_MODEL", "mistral-large-latest"),
        LLM_BASE_URL=os.getenv("LLM_BASE_URL", "https://api.mistral.ai/v1"),
        DATA_DIR=os.getenv("DATA_DIR", "./data"),
        MEDIA_DIR=os.getenv("MEDIA_DIR", "./data/inbound"),
        DB_PATH=os.getenv("DB_PATH", "./data/memory.db"),
        RETENTION_DAYS=int(os.getenv("RETENTION_DAYS", "90")),
        ALLOWED_USER_IDS=_parse_allowed_user_ids(os.getenv("ALLOWED_USER_IDS", "")),
        SENDER_NAMES=_parse_sender_names(os.getenv("SENDER_NAMES", "")),
    )


cfg = _load()


def reload() -> Config:
    global cfg
    cfg = _load()
    return cfg
