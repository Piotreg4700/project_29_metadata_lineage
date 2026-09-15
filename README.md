# Project 29 - Metadata, Lineage and Data Catalog for Weather Processing

Course: *Autonomous Expert Systems and Data Exploration*.

**Goal:** track where weather data comes from, how it changes through each
processing step, and which outputs depend on each step - i.e. build a
**data catalog + lineage + schema registry** on top of a real data pipeline.

This project does **not** invent data: it ingests from the shared Weather REST API,
persists raw payloads, validates/cleans them, builds curated features, and produces
an analytical report. At every step it captures metadata and lineage automatically.

## Architecture

```
Weather REST API
      |  (raw JSON persisted)
      v
[Bronze]  weather_bronze      -- raw measurements + ingestion metadata
      v
[Silver]  weather_silver      -- validated, de-duplicated, type-cast (+ quarantine)
      v
[Gold]    weather_hourly_gold -- hourly per-station features + comfort index
      v
[Report]  station_summary     -- per-station analytical summary

           +--------------------------------------------+
every step | Catalog engine: schemas, runs, dataset &   |
feeds ---> | column lineage, metrics, content hashes    |
           +--------------------------------------------+
                          |
        auto-generated docs: data catalog, lineage diagram,
        lineage tables, run log, impact analysis
```

## Project layout

| Path | Purpose |
|---|---|
| `config.py` | API URL/token, storage paths |
| `src/catalog.py` | **Core**: metadata model + lineage graph + impact analysis + persistence |
| `src/ingest.py` | Bronze: fetch from API, persist raw JSON |
| `src/validate.py` | Silver: validation rules, dedup, quarantine |
| `src/transform.py` | Gold: hourly aggregation + rule-based comfort index |
| `src/report.py` | Report: per-station summary dataset |
| `src/docs.py` | Documentation automation (catalog.md, lineage, impact) |
| `src/pipeline.py` | Orchestrator (entry point) |
| `impact_query.py` | Ad-hoc impact-analysis CLI over the saved catalog |
| `data/` | bronze / silver / gold / reports (created at runtime) |
| `catalog/catalog.json` | Machine-readable catalog (the single source of truth) |
| `docs_generated/` | Human-readable, auto-generated documentation |

## How to run

```bash
pip install -r requirements.txt

# optional: override the token instead of using the default in config.py
# Windows PowerShell:  $env:WEATHER_API_TOKEN="STUDENT_TOKEN_2026"

python -m src.pipeline                       # full pipeline + docs
python -m src.pipeline --stations GDN_01 GDY_01 --limit 50

# impact analysis (after the pipeline has run once)
python impact_query.py --asset weather_silver
python impact_query.py --column weather_bronze.temperature
```

## Deliverables produced (map to the project brief)

- **One-page HTML report (open in a browser)** -> `docs_generated/report.html`
  (catalog + rendered lineage diagram + schemas + run log + impact analysis in one file)
- **Data catalog** -> `catalog/catalog.json` + `docs_generated/data_catalog.md`
- **Lineage diagram/table** -> `docs_generated/lineage.mmd` (Mermaid), `lineage_edges.csv`, `column_lineage.csv`
- **Schema documentation** -> column tables in `data_catalog.md` (type, nullability, null count, lineage, description)
- **Impact-analysis examples** -> `docs_generated/impact_analysis.md` + `impact_query.py`
- **Run / transformation metadata** -> `docs_generated/runs.csv`

## What the catalog captures per step

- **Table metadata:** layer, location, format, row count, content hash, producing run.
- **Schema registry:** every column with logical type, pandas dtype, nullability, null count, description.
- **Dataset lineage:** edges `weather_api -> bronze -> silver -> gold -> report`.
- **Column lineage:** e.g. `station_summary.comfort_label` traces back to
  `weather_silver.temperature/humidity/wind_speed` and ultimately to the API.
- **Run metadata:** run id, step, code reference, inputs/outputs, params, metrics
  (rows in/out, duplicates removed, quality score), timestamps, status, environment.



## Assumptions, limitations, improvements

- **Assumptions:** API schema is stable; plausible value ranges in `validate.py`.
- **Limitations:** lineage is captured at run time from explicit declarations
  (not parsed from arbitrary code); no scheduler; local files instead of S3/Glue.
- **Improvements:** push the catalog to AWS Glue Data Catalog / Athena; schedule
  ingestion; add schema-change detection (compare `content_hash`/schema across runs);
  render the Mermaid lineage in a small dashboard.
