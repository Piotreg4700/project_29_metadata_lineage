from __future__ import annotations

import pandas as pd

import config
from src.catalog import Catalog

VALID_RANGES = {
    "temperature": (-60.0, 60.0),
    "humidity": (0.0, 100.0),
    "pressure": (850.0, 1100.0),
    "wind_speed": (0.0, 120.0),
    "wind_direction": (0.0, 360.0),
    "rain_mm": (0.0, 500.0),
    "cloud_cover": (0.0, 100.0),
}

_SILVER_COLUMN_DESCRIPTIONS = {
    "timestamp": "Sparsowany czas pomiaru (ze strefa czasowa, UTC).",
    "station_id": "Identyfikator stacji pogodowej.",
    "temperature": "Zwalidowana temperatura powietrza (Celsjusz) w wiarygodnym zakresie.",
    "humidity": "Zwalidowana wilgotnosc wzgledna (%).",
    "pressure": "Zwalidowane cisnienie atmosferyczne (hPa).",
    "wind_speed": "Zwalidowana predkosc wiatru (m/s).",
    "wind_direction": "Zwalidowany kierunek wiatru (stopnie).",
    "rain_mm": "Zwalidowany opad deszczu (mm).",
    "cloud_cover": "Zwalidowane zachmurzenie (%).",
    "is_valid": "True, jesli wiersz przeszedl wszystkie reguly walidacji.",
}


def validate(catalog: Catalog, bronze: pd.DataFrame) -> pd.DataFrame:
    run = catalog.start_run(step="validate", inputs=["weather_bronze"])

    try:
        df = bronze.copy()
        n_in = len(df)

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

        numeric_cols = [c for c in VALID_RANGES if c in df.columns]
        for c in numeric_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        before_dedup = len(df)
        df = df.drop_duplicates(subset=["station_id", "timestamp"]).reset_index(drop=True)
        duplicates_removed = before_dedup - len(df)

        valid = df["timestamp"].notna()
        for c, (lo, hi) in VALID_RANGES.items():
            if c in df.columns:
                valid &= df[c].between(lo, hi) | df[c].isna()
        df["is_valid"] = valid

        invalid = df[~df["is_valid"]]
        clean = df[df["is_valid"]].reset_index(drop=True)

        quarantine_path = config.SILVER_DIR / "weather_quarantine.parquet"
        if not invalid.empty:
            invalid.to_parquet(quarantine_path, index=False)

        keep_cols = ["timestamp", "station_id", *numeric_cols, "is_valid"]
        clean = clean[[c for c in keep_cols if c in clean.columns]]

        silver_path = config.SILVER_DIR / "weather_silver.parquet"
        clean.to_parquet(silver_path, index=False)

        col_lineage = {
            c: [f"weather_bronze.{c}"] for c in clean.columns if c != "is_valid"
        }
        col_lineage["is_valid"] = [f"weather_bronze.{c}" for c in numeric_cols] + [
            "weather_bronze.timestamp"
        ]

        catalog.register_asset(
            clean,
            name="weather_silver",
            layer="silver",
            description="Zwalidowane, odduplikowane i przerzutowane pomiary (tylko poprawne wiersze).",
            location=silver_path,
            fmt="parquet",
            run=run,
            column_descriptions=_SILVER_COLUMN_DESCRIPTIONS,
            column_lineage=col_lineage,
        )

        catalog.finish_run(run, status="success", metrics={
            "rows_in": int(n_in),
            "rows_out": int(len(clean)),
            "duplicates_removed": int(duplicates_removed),
            "invalid_quarantined": int(len(invalid)),
            "quality_score": round(len(clean) / n_in, 4) if n_in else 0.0,
        })
        return clean
    except Exception as exc:
        catalog.finish_run(run, status="failed", metrics={"error": str(exc)})
        raise
