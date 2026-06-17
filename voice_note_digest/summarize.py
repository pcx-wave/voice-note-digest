import logging
import requests
from .config import cfg

logger = logging.getLogger(__name__)


def summarize(transcript: str, speaker: str, style_prompts: dict) -> tuple[str, str]:
    style = style_prompts.get(speaker) or style_prompts.get("default", "Summarize concisely in 2-3 sentences.")
    prompt = style + " Also output a final line 'KEYWORDS: a, b, c'."
    url = f"{cfg.LLM_BASE_URL}/chat/completions"
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {cfg.LLM_API_KEY}"},
            json={
                "model": cfg.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": transcript},
                ],
                "temperature": 0.2,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if "KEYWORDS:" in content:
            parts = content.split("KEYWORDS:", 1)
            summary = parts[0].strip()
            keywords_csv = parts[1].strip()
        else:
            summary = content.strip()
            keywords_csv = ""
        return summary, keywords_csv
    except requests.RequestException as e:
        logger.exception("LLM summarize request failed")
        raise RuntimeError(f"LLM summarize failed: {e}")
