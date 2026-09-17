from __future__ import annotations

import os
from pathlib import Path

API_BASE_URL = "https://e6uw49pbah.execute-api.us-east-1.amazonaws.com/dev"
API_TOKEN = os.environ.get("WEATHER_API_TOKEN", "STUDENT_TOKEN_2026")

DEFAULT_STATIONS = ["GDN_01", "GDN_02", "GDY_01", "SOP_01"]
BATCH_LIMIT = 100
REQUEST_TIMEOUT = 30

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
REPORT_DIR = DATA_DIR / "reports"

DOCS_DIR = ROOT / "docs_generated"


def ensure_dirs() -> None:
    for d in (BRONZE_DIR, SILVER_DIR, GOLD_DIR, REPORT_DIR, DOCS_DIR):
        d.mkdir(parents=True, exist_ok=True)
