"""Shared paths and helpers for the KAMouflage Vision data scripts."""

import csv
import json
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

USER_AGENT = "KAMouflageVision-hackathon/0.1 (UAE Hackathon 2026 research prototype)"

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def http_get(url, **kwargs):
    return http_request("GET", url, **kwargs)


def http_request(method, url, *, retries=4, timeout=60, session=None, **kwargs):
    """HTTP request with simple retry/backoff (also on dropped connections). Raises on final failure."""
    s = session or _session
    for attempt in range(1, retries + 1):
        try:
            r = s.request(method, url, timeout=timeout, **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 * attempt)


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def log(msg):
    print(msg, flush=True)
