# voice-note-digest

A standalone Telegram bot that turns forwarded voice notes into a **persistent, per-speaker, correctable memory** — not just a transcript.

Most "voice → text" bots transcribe and forget. This one:

- **Transcribes** each voice note (cloud STT — OpenAI / Azure / Mistral).
- **Identifies the speaker** (optional, local, via resemblyzer) and applies a **per-speaker summary style** (a verbose relative gets compressed to decisions; a concise one stays faithful).
- **Remembers** every note in a SQLite store that **survives restarts** — deterministically, in code, not at the mercy of a model "remembering" to write it down.
- **Lets you correct it**: tell the bot it misunderstood and it updates that note in place, keeping a trace.

It deliberately does **no local transcription model** — that's too heavy for small devices (e.g. a Raspberry Pi). Transcription is a single API call.

## Why it exists

Built after wiring the same capability into an LLM agent and finding the agent layer made the memory writes *probabilistic* (the model had to choose to log). Pulling it into a standalone bot makes persist / recall / correct **guaranteed**.

## Architecture

```
Telegram voice ─► download .ogg ─► STT (API) ─► speaker ID (optional, local)
              ─► LLM summary (per-speaker style) ─► SQLite memory  ◄─ deterministic
/recall <q>   ─► query memory
/correct <txt>─► update the last note in place (+ correction trace)
retention.py  ─► purge audio > N days; summaries kept forever
```

Modules (`voice_note_digest/`):

| File | Role |
|------|------|
| `config.py` | env-driven config (`cfg`) |
| `stt.py` | provider-agnostic transcription |
| `speaker.py` | optional resemblyzer speaker ID (degrades to "unknown") |
| `summarize.py` | LLM summary with per-speaker prompt styles |
| `memory.py` | SQLite store: `add_note` / `find_notes` / `correct_note` |
| `pipeline.py` | one-note orchestration |
| `bot.py` | Telegram handlers + entrypoint |
| `retention.py` | purge old audio, keep summaries |

## Setup

```bash
git clone <this-repo> && cd voice-note-digest
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in tokens/keys
cp prompts.example.yaml prompts.yaml   # tune per-speaker styles
python -m voice_note_digest.bot
```

Get a bot token from [@BotFather](https://t.me/BotFather). Set `STT_*` and `LLM_*` for your providers in `.env`.

### Optional: per-speaker attribution

```bash
pip install resemblyzer numpy      # heavier; ffmpeg required on PATH
# add reference voices:
#   data/voice_samples/alice/sample.wav
#   data/voice_samples/bob/sample.wav
```
Folder names must match the keys in `prompts.yaml`. Without this, every note is `unknown` and uses the `default` style — the bot still works.

## Usage

- **Forward / send a voice note** → bot replies `[speaker] summary` and stores it.
- `/recall <query>` → search past notes (speaker, summary, transcript, keywords). No query = 10 most recent.
- `/correct <the right version>` → fix the most recent note in place; the correction is timestamped and kept.
- `/name <label>` → enroll the most recent voice as `<label>` (saves a reference sample) **and** relabels the note. Build your speaker set just by naming voices in chat.
- `/relabel <label>` → fix a wrong speaker attribution on the most recent note (DB only, no enrollment).

### Naming / author attribution

Three layers, strongest first:
1. **Sender override** — `SENDER_NAMES=123456789:Paul` in `.env` forces a name for a given Telegram sender, regardless of voice.
2. **Enrollment** — `/name <label>` registers a reference voice; future notes matching it are auto-attributed.
3. **Biometric match** — resemblyzer against `data/voice_samples/<label>/sample.wav` (optional). Falls back to `unknown`.

## Retention

```bash
python -m voice_note_digest.retention   # delete audio older than RETENTION_DAYS
```
Run it from cron daily. The SQLite memory is never purged.

## License

MIT — see [LICENSE](LICENSE).
