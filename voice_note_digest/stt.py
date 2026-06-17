import logging
import os
import requests
from .config import cfg

logger = logging.getLogger(__name__)


def transcribe(audio_path: str) -> str:
    provider = cfg.STT_PROVIDER
    if provider in ("openai", "mistral"):
        base = cfg.LLM_BASE_URL if provider == "mistral" else "https://api.openai.com/v1"
        url = f"{base}/audio/transcriptions"
        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    url,
                    files={"file": f},
                    data={"model": cfg.STT_MODEL},
                    headers={"Authorization": f"Bearer {cfg.STT_API_KEY}"},
                )
                response.raise_for_status()
                return response.json()["text"]
        except requests.RequestException as e:
            logger.exception("STT request failed")
            raise RuntimeError(f"STT failed: {e}")
    elif provider == "azure":
        endpoint = os.getenv("AZURE_STT_ENDPOINT")
        if not endpoint:
            raise ValueError("AZURE_STT_ENDPOINT not set")
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            response = requests.post(
                endpoint,
                data=audio_bytes,
                headers={
                    "Ocp-Apim-Subscription-Key": cfg.STT_API_KEY,
                    "Content-Type": "audio/ogg",
                },
            )
            response.raise_for_status()
            result = response.json()
            if "DisplayText" in result:
                return result["DisplayText"]
            if "combinedPhrases" in result and len(result["combinedPhrases"]) > 0:
                return result["combinedPhrases"][0].get("text", "")
            return ""
        except requests.RequestException as e:
            logger.exception("STT request failed")
            raise RuntimeError(f"STT failed: {e}")
    else:
        raise ValueError(f"Unknown STT provider: {provider}")
