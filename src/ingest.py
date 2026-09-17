from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import requests

import config
from src.catalog import Catalog

_RAW_COLUMN_DESCRIPTIONS = {
    "timestamp": "Czas pomiaru zwrocony przez API (ISO-8601, UTC).",
    "station_id": "Identyfikator stacji pogodowej.",
    "temperature": "Temperatura powietrza w stopniach Celsjusza.",
    "humidity": "Wilgotnosc wzgledna w procentach.",
    "pressure": "Cisnienie atmosferyczne w hPa.",
    "wind_speed": "Predkosc wiatru (m/s).",
    "wind_direction": "Kierunek wiatru w stopniach (0-359).",
    "rain_mm": "Opad deszczu w milimetrach.",
    "cloud_cover": "Zachmurzenie w procentach.",
    "_ingested_at": "Znacznik czasu pobrania dodany przez warstwe Bronze (metadane lineage).",
    "_source_file": "Sciezka surowego pliku JSON, z ktorego wczytano ten wiersz (metadane lineage).",
}


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {config.API_TOKEN}"}


def fetch_stations() -> list[str]:
    url = f"{config.API_BASE_URL}/weather/stations"
    resp = requests.get(url, headers=_headers(), timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("stations", [])


def fetch_batch(station_id: str, limit: int) -> dict:
    url = f"{config.API_BASE_URL}/weather/batch"
    params = {"station_id": station_id, "limit": limit}
    resp = requests.get(url, headers=_headers(), params=params,
                        timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def ingest(catalog: Catalog, stations: list[str] | None = None,
           limit: int | None = None) -> pd.DataFrame:
    limit = limit or config.BATCH_LIMIT
    run = catalog.start_run(step="ingest", inputs=["weather_api"])

    try:
        if stations is None:
            stations = fetch_stations()

        run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rows: list[dict] = []
        raw_files: list[str] = []

        for station in stations:
            payload = fetch_batch(station, limit)
            raw_path = config.BRONZE_DIR / f"raw_{station}_{run_stamp}.json"
            raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            raw_files.append(str(raw_path))

            for rec in payload.get("records", []):
                rec = dict(rec)
                rec["_ingested_at"] = datetime.now(timezone.utc).isoformat()
                rec["_source_file"] = str(raw_path)
                rows.append(rec)

        df = pd.DataFrame(rows)
        bronze_path = config.BRONZE_DIR / "weather_bronze.parquet"
        df.to_parquet(bronze_path, index=False)

        catalog.register_asset(
            df,
            name="weather_bronze",
            layer="bronze",
            description=(
                "Surowe pomiary pogodowe pobrane z REST API, jeden wiersz na pomiar, "
                "wzbogacone o metadane pobrania. Bez zadnego czyszczenia."
            ),
            location=bronze_path,
            fmt="parquet",
            run=run,
            column_descriptions=_RAW_COLUMN_DESCRIPTIONS,
            column_lineage={c: ["weather_api.records"] for c in df.columns},
        )

        catalog.finish_run(run, status="success", metrics={
            "stations": len(stations),
            "raw_files_written": len(raw_files),
            "rows_ingested": int(len(df)),
        })
        return df
    except Exception as exc:
        catalog.finish_run(run, status="failed", metrics={"error": str(exc)})
        raise
