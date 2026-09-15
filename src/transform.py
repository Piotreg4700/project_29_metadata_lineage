from __future__ import annotations

import pandas as pd

import config
from src.catalog import Catalog

_GOLD_COLUMN_DESCRIPTIONS = {
    "station_id": "Identyfikator stacji pogodowej.",
    "hour": "Kubelek godzinowy (UTC), po ktorym agregowane sa metryki.",
    "avg_temperature": "Srednia temperatura w danej godzinie.",
    "avg_humidity": "Srednia wilgotnosc wzgledna w danej godzinie.",
    "avg_pressure": "Srednie cisnienie w danej godzinie.",
    "max_wind_speed": "Maksymalna predkosc wiatru w danej godzinie.",
    "total_rain_mm": "Sumaryczny opad deszczu w danej godzinie.",
    "avg_cloud_cover": "Srednie zachmurzenie w danej godzinie.",
    "n_measurements": "Liczba poprawnych pomiarow zagregowanych w kubelku.",
    "comfort_index": "Prosty regulowy wskaznik komfortu (0-100) z temperatury/wilgotnosci/wiatru.",
}


def _comfort_index(row: pd.Series) -> float:
    temp_pen = abs(row["avg_temperature"] - 21.0) * 2.5
    hum_pen = max(0.0, row["avg_humidity"] - 60.0) * 0.5
    wind_pen = row["max_wind_speed"] * 1.5
    score = 100.0 - temp_pen - hum_pen - wind_pen
    return round(max(0.0, min(100.0, score)), 1)


def transform(catalog: Catalog, silver: pd.DataFrame) -> pd.DataFrame:
    run = catalog.start_run(
        step="transform",
        description="Agregacja danych Silver do godzinowych cech Gold per stacja, wraz ze wskaznikiem komfortu.",
        code_ref="src.transform:transform",
        inputs=["weather_silver"],
        params={"grain": "station_id x hour"},
    )

    try:
        df = silver.copy()
        df["hour"] = df["timestamp"].dt.floor("h")

        grouped = df.groupby(["station_id", "hour"], as_index=False).agg(
            avg_temperature=("temperature", "mean"),
            avg_humidity=("humidity", "mean"),
            avg_pressure=("pressure", "mean"),
            max_wind_speed=("wind_speed", "max"),
            total_rain_mm=("rain_mm", "sum"),
            avg_cloud_cover=("cloud_cover", "mean"),
            n_measurements=("temperature", "size"),
        )
        for c in ["avg_temperature", "avg_humidity", "avg_pressure",
                  "max_wind_speed", "total_rain_mm", "avg_cloud_cover"]:
            grouped[c] = grouped[c].round(2)

        grouped["comfort_index"] = grouped.apply(_comfort_index, axis=1)

        gold_path = config.GOLD_DIR / "weather_hourly_gold.parquet"
        grouped.to_parquet(gold_path, index=False)

        col_lineage = {
            "station_id": ["weather_silver.station_id"],
            "hour": ["weather_silver.timestamp"],
            "avg_temperature": ["weather_silver.temperature"],
            "avg_humidity": ["weather_silver.humidity"],
            "avg_pressure": ["weather_silver.pressure"],
            "max_wind_speed": ["weather_silver.wind_speed"],
            "total_rain_mm": ["weather_silver.rain_mm"],
            "avg_cloud_cover": ["weather_silver.cloud_cover"],
            "n_measurements": ["weather_silver.temperature"],
            "comfort_index": [
                "weather_silver.temperature",
                "weather_silver.humidity",
                "weather_silver.wind_speed",
            ],
        }

        catalog.register_asset(
            grouped,
            name="weather_hourly_gold",
            layer="gold",
            description="Wyselekcjonowane godzinowe cechy pogodowe per stacja oraz regulowy wskaznik komfortu.",
            location=gold_path,
            fmt="parquet",
            run=run,
            column_descriptions=_GOLD_COLUMN_DESCRIPTIONS,
            column_lineage=col_lineage,
        )

        catalog.finish_run(run, status="success", metrics={
            "rows_out": int(len(grouped)),
            "stations": int(grouped["station_id"].nunique()),
        })
        return grouped
    except Exception as exc:
        catalog.finish_run(run, status="failed", metrics={"error": str(exc)})
        raise
