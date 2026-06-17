import sqlite3
from datetime import datetime


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row is not None else None


def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audio_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file TEXT UNIQUE NOT NULL,
                received_at TEXT,
                speaker TEXT,
                confidence REAL,
                transcript TEXT,
                summary TEXT,
                keywords TEXT,
                corrections TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()


def add_note(db_path: str, file: str, received_at: str, speaker: str,
             confidence: float = None, transcript: str = None,
             summary: str = None, keywords: str = None) -> int:
    now = _now()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT INTO audio_notes
            (file, received_at, speaker, confidence, transcript, summary, keywords, corrections, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '', ?)
            ON CONFLICT(file) DO UPDATE SET
                speaker = COALESCE(excluded.speaker, speaker),
                confidence = COALESCE(excluded.confidence, confidence),
                transcript = COALESCE(excluded.transcript, transcript),
                summary = COALESCE(excluded.summary, summary),
                keywords = COALESCE(excluded.keywords, keywords),
                updated_at = ?
        """, (file, received_at, speaker, confidence, transcript, summary, keywords, now, now))
        conn.commit()
        row = conn.execute("SELECT id FROM audio_notes WHERE file = ?", (file,)).fetchone()
        return row[0]


def get_note(db_path: str, file: str) -> dict | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM audio_notes WHERE file = ?", (file,)
        ).fetchone()
        return _row_to_dict(row)


def find_notes(db_path: str, query: str, limit: int = 10) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        pattern = f"%{query}%"
        rows = conn.execute("""
            SELECT * FROM audio_notes
            WHERE speaker LIKE ? COLLATE NOCASE
               OR summary LIKE ? COLLATE NOCASE
               OR transcript LIKE ? COLLATE NOCASE
               OR keywords LIKE ? COLLATE NOCASE
            ORDER BY received_at DESC
            LIMIT ?
        """, (pattern, pattern, pattern, pattern, limit)).fetchall()
        return [_row_to_dict(row) for row in rows]


def recent(db_path: str, n: int = 10) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM audio_notes
            ORDER BY received_at DESC
            LIMIT ?
        """, (n,)).fetchall()
        return [_row_to_dict(row) for row in rows]


def correct_note(db_path: str, file: str, correction: str, new_summary: str = None) -> dict | None:
    now = _now()
    correction_line = f"[{now}] {correction}"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT corrections FROM audio_notes WHERE file = ?", (file,)
        ).fetchone()
        if not row:
            return None

        current_corrections = row['corrections']
        if current_corrections:
            new_corrections = current_corrections + "\n" + correction_line
        else:
            new_corrections = correction_line

        if new_summary is not None:
            conn.execute("""
                UPDATE audio_notes
                SET corrections = ?, summary = ?, updated_at = ?
                WHERE file = ?
            """, (new_corrections, new_summary, now, file))
        else:
            conn.execute("""
                UPDATE audio_notes
                SET corrections = ?, updated_at = ?
                WHERE file = ?
            """, (new_corrections, now, file))
        conn.commit()

        updated_row = conn.execute(
            "SELECT * FROM audio_notes WHERE file = ?", (file,)
        ).fetchone()
        return _row_to_dict(updated_row)


def set_speaker(db_path: str, file: str, speaker: str) -> dict | None:
    now = _now()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("""
            UPDATE audio_notes
            SET speaker = ?, updated_at = ?
            WHERE file = ?
        """, (speaker, now, file))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM audio_notes WHERE file = ?", (file,)
        ).fetchone()
        return _row_to_dict(row)
