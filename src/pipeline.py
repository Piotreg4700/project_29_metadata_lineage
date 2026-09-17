from __future__ import annotations

import argparse

import config
from src import docs, ingest, report, transform, validate
from src.catalog import Catalog


def run_pipeline(stations: list[str] | None = None, limit: int | None = None) -> Catalog:
    config.ensure_dirs()
    cat = Catalog()

    print(f"[pipeline] run id = {cat.pipeline_run_id}")

    bronze = ingest.ingest(cat, stations=stations, limit=limit)
    print(f"[ingest]   bronze rows: {len(bronze)}")

    silver = validate.validate(cat, bronze)
    print(f"[validate] silver rows: {len(silver)}")

    gold = transform.transform(cat, silver)
    print(f"[transform] gold rows:  {len(gold)}")

    summary = report.report(cat, gold)
    print(f"[report]   summary rows: {len(summary)}")

    html = docs.generate_html_report(cat)
    print(f"[docs]     report.html -> {html}")

    return cat


def main() -> None:
    parser = argparse.ArgumentParser(description="Weather metadata/lineage pipeline (Projekt 29)")
    parser.add_argument("--stations", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run_pipeline(stations=args.stations, limit=args.limit)


if __name__ == "__main__":
    main()
