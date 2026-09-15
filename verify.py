from __future__ import annotations

import glob
import json
import sys

import pandas as pd

import config
from src.catalog import Catalog
from src.transform import _comfort_index
from src.report import _label
from src.validate import VALID_RANGES

PASS, FAIL = 0, 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    mark = "OK  " if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"[{mark}] {name}" + (f" -> {detail}" if detail else ""))


def main() -> None:
    if not config.CATALOG_JSON.exists():
        raise SystemExit("Brak catalog.json. Najpierw uruchom: python -m src.pipeline")

    cat = Catalog.load(config.CATALOG_JSON)

    bronze = pd.read_parquet(config.BRONZE_DIR / "weather_bronze.parquet")
    silver = pd.read_parquet(config.SILVER_DIR / "weather_silver.parquet")
    gold = pd.read_parquet(config.GOLD_DIR / "weather_hourly_gold.parquet")
    summary = pd.read_csv(config.REPORT_DIR / "station_summary.csv")

    print("\n=== 1. Liczby wierszy w katalogu == pliki na dysku ===")
    check("weather_bronze row_count", cat.assets["weather_bronze"].row_count == len(bronze),
          f"katalog={cat.assets['weather_bronze'].row_count}, plik={len(bronze)}")
    check("weather_silver row_count", cat.assets["weather_silver"].row_count == len(silver),
          f"katalog={cat.assets['weather_silver'].row_count}, plik={len(silver)}")
    check("weather_hourly_gold row_count", cat.assets["weather_hourly_gold"].row_count == len(gold),
          f"katalog={cat.assets['weather_hourly_gold'].row_count}, plik={len(gold)}")
    check("station_summary row_count", cat.assets["station_summary"].row_count == len(summary),
          f"katalog={cat.assets['station_summary'].row_count}, plik={len(summary)}")

    print("\n=== 2. Schemat w katalogu == kolumny w pliku ===")
    for asset_name, df in [("weather_bronze", bronze), ("weather_silver", silver),
                           ("weather_hourly_gold", gold), ("station_summary", summary)]:
        cat_cols = [c.name for c in cat.assets[asset_name].columns]
        check(f"{asset_name} kolumny", cat_cols == list(df.columns),
              f"katalog={cat_cols} vs plik={list(df.columns)}")

    print("\n=== 3. Suma kontrolna (hash) katalogu == przeliczona z pliku ===")
    for asset_name, df in [("weather_bronze", bronze), ("weather_silver", silver),
                           ("weather_hourly_gold", gold)]:
        recomputed = Catalog._hash_df(df)
        check(f"{asset_name} hash", recomputed == cat.assets[asset_name].content_hash,
              f"katalog={cat.assets[asset_name].content_hash}, przeliczony={recomputed}")

    print("\n=== 4. Bronze == suma rekordow w surowych plikach JSON ===")
    raw_total = 0
    for fp in glob.glob(str(config.BRONZE_DIR / "raw_*.json")):
        raw_total += len(json.loads(open(fp, encoding="utf-8").read()).get("records", []))
    check("Bronze niepuste", len(bronze) > 0, f"wierszy={len(bronze)}")
    check("Surowe JSON istnieja i maja rekordy", raw_total >= len(bronze),
          f"rekordow w JSON (lacznie)={raw_total}, bronze={len(bronze)}")

    print("\n=== 5. Silver: tylko poprawne wiersze, brak duplikatow ===")
    check("Silver: wszystkie is_valid == True", bool(silver["is_valid"].all()))
    dup = silver.duplicated(subset=["station_id", "timestamp"]).sum()
    check("Silver: brak duplikatow (station_id, timestamp)", dup == 0, f"duplikatow={dup}")
    in_range = True
    for col, (lo, hi) in VALID_RANGES.items():
        if col in silver.columns:
            in_range &= bool(silver[col].between(lo, hi).all())
    check("Silver: wszystkie wartosci w dozwolonych zakresach", in_range)

    print("\n=== 6. Gold: niezalezne przeliczenie z Silver ===")
    s = silver.copy()
    s["timestamp"] = pd.to_datetime(s["timestamp"], utc=True)
    s["hour"] = s["timestamp"].dt.floor("h")
    expected_gold = s.groupby(["station_id", "hour"], as_index=False).agg(
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
        expected_gold[c] = expected_gold[c].round(2)
    expected_gold["comfort_index"] = expected_gold.apply(_comfort_index, axis=1)

    check("Gold: liczba wierszy zgodna", len(expected_gold) == len(gold),
          f"przeliczono={len(expected_gold)}, plik={len(gold)}")
    g1 = gold.sort_values(["station_id", "hour"]).reset_index(drop=True)
    g2 = expected_gold.sort_values(["station_id", "hour"]).reset_index(drop=True)
    g1["hour"] = pd.to_datetime(g1["hour"], utc=True)
    same = g1[["avg_temperature", "max_wind_speed", "total_rain_mm",
               "n_measurements", "comfort_index"]].equals(
           g2[["avg_temperature", "max_wind_speed", "total_rain_mm",
               "n_measurements", "comfort_index"]])
    check("Gold: wartosci kluczowych kolumn identyczne", same)

    print("\n=== 7. Report: niezalezne przeliczenie z Gold ===")
    expected_summary = gold.groupby("station_id", as_index=False).agg(
        hours_covered=("hour", "nunique"),
        avg_temperature=("avg_temperature", "mean"),
        avg_comfort_index=("comfort_index", "mean"),
        total_rain_mm=("total_rain_mm", "sum"),
        peak_wind_speed=("max_wind_speed", "max"),
    )
    expected_summary["avg_comfort_index"] = expected_summary["avg_comfort_index"].round(1)
    expected_summary["comfort_label"] = expected_summary["avg_comfort_index"].apply(_label)
    m = summary.sort_values("station_id").reset_index(drop=True)
    e = expected_summary.sort_values("station_id").reset_index(drop=True)
    check("Report: liczba stacji zgodna", len(m) == len(e))
    check("Report: etykiety komfortu zgodne", list(m["comfort_label"]) == list(e["comfort_label"]),
          f"plik={list(m['comfort_label'])}, przeliczono={list(e['comfort_label'])}")
    check("Report: hours_covered zgodne", list(m["hours_covered"]) == list(e["hours_covered"]))

    print("\n=== 8. Spojnosc grafu lineage ===")
    known_cols = {f"{a}.{c.name}" for a, asset in cat.assets.items() for c in asset.columns}
    bad_refs = []
    for e_ in cat.column_edges:
        if e_.src.startswith("weather_api"):
            continue
        if e_.src not in known_cols:
            bad_refs.append(e_.src)
    check("Lineage kolumn: wszystkie zrodla istnieja", not bad_refs, f"nieznane={bad_refs[:5]}")
    down = cat.downstream_assets("weather_bronze")
    check("Lineage: z bronze osiagalny station_summary", "station_summary" in down,
          f"downstream={down}")

    print(f"\n=== WYNIK: {PASS} OK, {FAIL} FAIL ===")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
