# Project 29 - Metadata, Lineage and Data Catalog for Weather Processing

Course: *Autonomous Expert Systems and Data Exploration*.

**Goal:** track where weather data comes from, how it changes through each
processing step, and which outputs depend on each step.

Data comes from the shared Weather REST API. Raw payloads are saved before
cleaning. Each step records metadata and lineage. The result is one HTML report.

## Architecture

```
Weather REST API
      |  (raw JSON persisted)
      v
[Bronze]  weather_bronze      -- raw measurements + ingestion metadata
      v
[Silver]  weather_silver      -- validated, de-duplicated, type-cast
      v
[Gold]    weather_hourly_gold -- hourly per-station features + comfort index
      v
[Report]  station_summary     -- per-station analytical summary
      v
docs_generated/report.html    -- catalog, lineage, schemas, impact, results
```

## Project layout

| Path | Purpose |
|---|---|
| `config.py` | API URL/token, storage paths |
| `src/catalog.py` | metadata, lineage graph, impact analysis |
| `src/ingest.py` | Bronze: fetch from API, persist raw JSON |
| `src/validate.py` | Silver: validation, dedup, quarantine |
| `src/transform.py` | Gold: hourly aggregation + comfort index |
| `src/report.py` | per-station summary dataset |
| `src/docs.py` | generates `report.html` |
| `src/pipeline.py` | runs all steps |
| `data/` | bronze / silver / gold / reports (created at runtime) |
| `docs_generated/report.html` | final report |

## How to run

```bash
pip install -r requirements.txt
python -m src.pipeline
python -m src.pipeline --stations GDN_01 GDY_01 --limit 50
```

Open `docs_generated/report.html` in a browser.

## Deliverables (in report.html)

- data catalog and schema documentation
- lineage diagram
- run / transformation metrics
- impact-analysis examples
- analytical results (comfort index per station)

## Assumptions, limitations, improvements

- **Assumptions:** API schema is stable; plausible value ranges in `validate.py`.
- **Limitations:** lineage is declared in each step (not inferred from code); local files, no scheduler.
- **Improvements:** S3 / Glue Data Catalog / Athena; schema-change detection from `content_hash`.
