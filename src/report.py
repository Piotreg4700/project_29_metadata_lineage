from __future__ import annotations

import pandas as pd

import config
from src.catalog import Catalog

_REPORT_COLUMN_DESCRIPTIONS = {
    "station_id": "Identyfikator stacji pogodowej.",
    "hours_covered": "Liczba roznych kubelkow godzinowych dostepnych dla stacji.",
    "avg_temperature": "Srednia temperatura ze wszystkich kubelkow godzinowych.",
    "avg_comfort_index": "Sredni wskaznik komfortu ze wszystkich kubelkow godzinowych.",
    "total_rain_mm": "Sumaryczny opad deszczu ze wszystkich kubelkow godzinowych.",
    "peak_wind_speed": "Najwyzsza zaobserwowana godzinowa maksymalna predkosc wiatru.",
    "comfort_label": "Czytelna etykieta komfortu wyliczona z avg_comfort_index.",
}


def _label(score: float) -> str:
    if score >= 75:
        return "bardzo komfortowo"
    if score >= 55:
        return "komfortowo"
    if score >= 35:
        return "umiarkowanie"
    return "trudne warunki"


def report(catalog: Catalog, gold: pd.DataFrame) -> pd.DataFrame:
    run = catalog.start_run(step="report", inputs=["weather_hourly_gold"])

    try:
        summary = gold.groupby("station_id", as_index=False).agg(
            hours_covered=("hour", "nunique"),
            avg_temperature=("avg_temperature", "mean"),
            avg_comfort_index=("comfort_index", "mean"),
            total_rain_mm=("total_rain_mm", "sum"),
            peak_wind_speed=("max_wind_speed", "max"),
        )
        summary["avg_temperature"] = summary["avg_temperature"].round(2)
        summary["avg_comfort_index"] = summary["avg_comfort_index"].round(1)
        summary["total_rain_mm"] = summary["total_rain_mm"].round(2)
        summary["comfort_label"] = summary["avg_comfort_index"].apply(_label)

        report_path = config.REPORT_DIR / "station_summary.csv"
        summary.to_csv(report_path, index=False)

        col_lineage = {
            "station_id": ["weather_hourly_gold.station_id"],
            "hours_covered": ["weather_hourly_gold.hour"],
            "avg_temperature": ["weather_hourly_gold.avg_temperature"],
            "avg_comfort_index": ["weather_hourly_gold.comfort_index"],
            "total_rain_mm": ["weather_hourly_gold.total_rain_mm"],
            "peak_wind_speed": ["weather_hourly_gold.max_wind_speed"],
            "comfort_label": ["weather_hourly_gold.comfort_index"],
        }

        catalog.register_asset(
            summary,
            name="station_summary",
            layer="report",
            description="Analityczne podsumowanie per stacja uzywane przez raport/dashboard.",
            location=report_path,
            fmt="csv",
            run=run,
            column_descriptions=_REPORT_COLUMN_DESCRIPTIONS,
            column_lineage=col_lineage,
        )

        catalog.finish_run(run, status="success", metrics={"rows_out": int(len(summary))})
        return summary
    except Exception as exc:
        catalog.finish_run(run, status="failed", metrics={"error": str(exc)})
        raise
