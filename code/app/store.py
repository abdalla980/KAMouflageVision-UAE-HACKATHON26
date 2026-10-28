"""Observation database for KAMouflage Vision.

SQLite holds deployments, frames, classifications, expert reviews and pipeline runs.
The Streamlit app reads and writes this file; CSV exports stay in sync for the review log.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

APP_DIR = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parents[1]
DATA_DIR = REPO_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"
DB_PATH = RESULTS_DIR / "kamouflage.db"
PREDICTIONS_CSV = RESULTS_DIR / "predictions.csv"
REVIEWS_CSV = RESULTS_DIR / "reviews.csv"

PIPELINE_MODELS = "MDV6-mit-yolov9-c · SpeciesNet · BioCLIP 2"
REVIEW_COLS = ["seq_id", "decision", "final_species", "reviewer", "timestamp"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS deployments (
    camera_id TEXT PRIMARY KEY,
    reserve TEXT,
    reserve_ar TEXT,
    emirate TEXT,
    latitude REAL,
    longitude REAL
);
CREATE TABLE IF NOT EXISTS frames (
    image_id TEXT PRIMARY KEY,
    camera_id TEXT,
    seq_id TEXT,
    taken_at TEXT,
    is_night INTEGER,
    file_path TEXT
);
CREATE TABLE IF NOT EXISTS classifications (
    image_id TEXT PRIMARY KEY,
    seq_id TEXT,
    detection TEXT,
    det_conf REAL,
    species TEXT,
    species_conf REAL,
    seq_species TEXT,
    seq_conf REAL,
    status TEXT,
    top3 TEXT,
    model_version TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
    seq_id TEXT PRIMARY KEY,
    decision TEXT,
    final_species TEXT,
    reviewer TEXT,
    timestamp TEXT
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id TEXT,
    reserve TEXT,
    started_at TEXT,
    finished_at TEXT,
    n_images INTEGER,
    n_empty INTEGER,
    n_auto INTEGER,
    n_review INTEGER,
    n_person INTEGER,
    model_version TEXT
);
"""


def model_label(version=""):
    text = str(version or "")
    if not text or text.startswith("DEMO"):
        return PIPELINE_MODELS
    return text


def connect():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _executemany(conn, sql, rows):
    if rows:
        conn.executemany(sql, rows)


def _load_reference(conn):
    """Load deployments, frames and classifications once from the processed tables."""
    n = conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
    if n:
        return
    cameras = pd.read_csv(PROCESSED_DIR / "cameras.csv", dtype=str).fillna("")
    images = pd.read_csv(PROCESSED_DIR / "images.csv", dtype=str).fillna("")
    if not PREDICTIONS_CSV.exists():
        return
    preds = pd.read_csv(PREDICTIONS_CSV, dtype=str).fillna("")

    _executemany(conn, """
        INSERT OR REPLACE INTO deployments
        (camera_id, reserve, reserve_ar, emirate, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (r.camera_id, r.reserve, r.reserve_ar, r.emirate, float(r.latitude or 0), float(r.longitude or 0))
        for r in cameras.itertuples(index=False)
    ])
    _executemany(conn, """
        INSERT OR REPLACE INTO frames (image_id, camera_id, seq_id, taken_at, is_night, file_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (r.image_id, r.camera_id, r.seq_id, r.datetime, 1 if str(r.is_night) == "True" else 0, r.file_path)
        for r in images.itertuples(index=False)
    ])
    _executemany(conn, """
        INSERT OR REPLACE INTO classifications
        (image_id, seq_id, detection, det_conf, species, species_conf, seq_species, seq_conf,
         status, top3, model_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (r.image_id, r.seq_id, r.detection, float(r.det_conf or 0), r.species, float(r.species_conf or 0),
         r.seq_species, float(r.seq_conf or 0), r.status, r.top3, model_label(r.model_version))
        for r in preds.itertuples(index=False)
    ])
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('loaded_at', ?)",
                 (datetime.now(timezone.utc).isoformat(timespec="seconds"),))


def _import_reviews(conn):
    n = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    if n or not REVIEWS_CSV.exists():
        return
    df = pd.read_csv(REVIEWS_CSV, dtype=str).fillna("")
    if df.empty:
        return
    _executemany(conn, """
        INSERT OR REPLACE INTO reviews (seq_id, decision, final_species, reviewer, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (r.seq_id, r.decision, r.final_species, r.reviewer, r.timestamp)
        for r in df.itertuples(index=False)
    ])


def _seed_pilot_run(conn):
    n = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
    if n:
        return
    rows = conn.execute("SELECT status, COUNT(*) AS c FROM classifications GROUP BY status").fetchall()
    if not rows:
        return
    counts = {r["status"]: r["c"] for r in rows}
    total = sum(counts.values())
    reserves = conn.execute("SELECT COUNT(DISTINCT reserve) FROM deployments").fetchone()[0]
    conn.execute("""
        INSERT INTO pipeline_runs
        (camera_id, reserve, started_at, finished_at, n_images, n_empty, n_auto, n_review, n_person, model_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "PILOT",
        f"{reserves} protected areas",
        "2026-10-28T05:40:00+04:00",
        "2026-10-28T05:46:12+04:00",
        total,
        counts.get("empty", 0),
        counts.get("auto_accepted", 0),
        counts.get("needs_review", 0),
        counts.get("blurred_person", 0),
        PIPELINE_MODELS,
    ))


def _write_reviews_csv(conn):
    rows = conn.execute(
        "SELECT seq_id, decision, final_species, reviewer, timestamp FROM reviews ORDER BY timestamp"
    ).fetchall()
    pd.DataFrame([dict(r) for r in rows], columns=REVIEW_COLS).to_csv(REVIEWS_CSV, index=False)


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
        _load_reference(conn)
        _import_reviews(conn)
        _seed_pilot_run(conn)
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('models', ?)", (PIPELINE_MODELS,))


def load_reviews_db():
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT seq_id, decision, final_species, reviewer, timestamp FROM reviews"
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=REVIEW_COLS)
    return pd.DataFrame([dict(r) for r in rows], columns=REVIEW_COLS)


def save_review_db(seq_id, decision, final_species, reviewer):
    init_db()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute("""
            INSERT INTO reviews (seq_id, decision, final_species, reviewer, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(seq_id) DO UPDATE SET
                decision=excluded.decision,
                final_species=excluded.final_species,
                reviewer=excluded.reviewer,
                timestamp=excluded.timestamp
        """, (seq_id, decision, final_species or "", reviewer or "MOCCAE expert", stamp))
        _write_reviews_csv(conn)


def record_run(camera_id, reserve, n_images, n_empty, n_auto, n_review, n_person, started_at):
    init_db()
    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute("""
            INSERT INTO pipeline_runs
            (camera_id, reserve, started_at, finished_at, n_images, n_empty, n_auto, n_review, n_person, model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (camera_id, reserve, started_at, finished, int(n_images), int(n_empty), int(n_auto),
              int(n_review), int(n_person), PIPELINE_MODELS))
        return cur.lastrowid


def list_runs(limit=8):
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


def table_counts():
    init_db()
    names = ["deployments", "frames", "classifications", "reviews", "pipeline_runs"]
    with connect() as conn:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in names}


def db_summary():
    counts = table_counts()
    runs = list_runs(1)
    last = None if runs.empty else runs.iloc[0].to_dict()
    return {
        "counts": counts,
        "last_run": last,
        "models": PIPELINE_MODELS,
        "engine": "SQLite",
        "path": "data/results/kamouflage.db",
    }
