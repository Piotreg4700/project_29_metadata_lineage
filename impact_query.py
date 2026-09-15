from __future__ import annotations

import argparse

import config
from src.catalog import Catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Analiza wplywu na podstawie katalogu danych.")
    parser.add_argument("--asset")
    parser.add_argument("--column")
    args = parser.parse_args()

    if not config.CATALOG_JSON.exists():
        raise SystemExit("Brak katalogu. Najpierw uruchom: python -m src.pipeline")

    cat = Catalog.load(config.CATALOG_JSON)

    if args.asset:
        print(f"Zbior: {args.asset}")
        print("  zalezne (dotkniete przy zmianie):", cat.downstream_assets(args.asset) or "brak")
        print("  zaleznosci (od czego zalezy):    ", cat.upstream_assets(args.asset) or "brak")
    if args.column:
        print(f"Kolumna: {args.column}")
        print("  kolumny zalezne:", cat.downstream_columns(args.column) or "brak")
    if not args.asset and not args.column:
        parser.print_help()


if __name__ == "__main__":
    main()
