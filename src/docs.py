from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

import config
from src.catalog import Catalog

_LAYER_ORDER = {"bronze": 0, "silver": 1, "gold": 2, "report": 3}


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def generate_data_catalog(cat: Catalog, out_dir: Path) -> Path:
    lines = ["# Katalog danych - przetwarzanie danych pogodowych", ""]
    lines.append(f"- Identyfikator uruchomienia: `{cat.pipeline_run_id}`")
    lines.append(f"- Wygenerowano: {cat.to_dict()['generated_at']}")
    lines.append(f"- Zbiory danych: {len(cat.assets)} | Uruchomienia: {len(cat.runs)} | "
                 f"Krawedzie lineage: {len(cat.edges)}")
    lines.append("")

    for name, asset in sorted(cat.assets.items(),
                              key=lambda kv: (_LAYER_ORDER.get(kv[1].layer, 9), kv[0])):
        lines.append(f"## `{name}`  _( warstwa {asset.layer} )_")
        lines.append("")
        lines.append(f"- **Opis:** {asset.description}")
        lines.append(f"- **Lokalizacja:** `{asset.location}`")
        lines.append(f"- **Format:** {asset.fmt}")
        lines.append(f"- **Liczba wierszy:** {asset.row_count}")
        lines.append(f"- **Utworzone przez uruchomienie:** `{asset.produced_by_run}`")
        lines.append(f"- **Suma kontrolna (hash):** `{asset.content_hash}`")
        lines.append("")
        lines.append("| Kolumna | Typ | Dopuszcza puste | Liczba pustych | Pochodzi z | Opis |")
        lines.append("|---|---|---|---|---|---|")
        for c in asset.columns:
            src = "<br>".join(c.source_columns) if c.source_columns else "-"
            lines.append(
                f"| `{c.name}` | {c.dtype} | {c.nullable} | {c.null_count} | "
                f"{src} | {c.description} |"
            )
        lines.append("")

    path = out_dir / "data_catalog.md"
    _write(path, "\n".join(lines))
    return path


def _mermaid_graph(cat: Catalog) -> str:
    lines = ["graph LR"]
    lines.append('  weather_api["weather_api (REST)"]')
    for name, asset in cat.assets.items():
        lines.append(f'  {name}["{name}<br/>({asset.layer}, {asset.row_count} wierszy)"]')
    for e in cat.edges:
        lines.append(f"  {e.src} --> {e.dst}")
    return "\n".join(lines)


def generate_lineage_mermaid(cat: Catalog, out_dir: Path) -> Path:
    path = out_dir / "lineage.mmd"
    _write(path, _mermaid_graph(cat))
    return path


def generate_lineage_tables(cat: Catalog, out_dir: Path) -> tuple[Path, Path, Path]:
    edges_path = out_dir / "lineage_edges.csv"
    with edges_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["zrodlo", "cel", "id_uruchomienia", "rodzaj"])
        for e in cat.edges:
            w.writerow([e.src, e.dst, e.run_id, e.kind])

    col_path = out_dir / "column_lineage.csv"
    with col_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kolumna_zrodlowa", "kolumna_docelowa", "id_uruchomienia"])
        for e in cat.column_edges:
            w.writerow([e.src, e.dst, e.run_id])

    runs_path = out_dir / "runs.csv"
    with runs_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id_uruchomienia", "krok", "status", "wejscia", "wyjscia",
                    "czas_startu", "czas_konca", "metryki"])
        for r in cat.runs:
            w.writerow([r.run_id, r.step, r.status, ";".join(r.inputs),
                        ";".join(r.outputs), r.started_at, r.finished_at, r.metrics])
    return edges_path, col_path, runs_path


def generate_impact_analysis(cat: Catalog, out_dir: Path) -> Path:
    lines = ["# Przyklady analizy wplywu", ""]
    lines.append("Analiza wplywu odpowiada na pytanie: *jesli ten zbior/kolumna zmieni "
                 "sie lub przestanie dzialac, ktore wyniki ponizej zostana dotkniete?* "
                 "Jest wyliczana automatycznie z zarejestrowanego grafu lineage.")
    lines.append("")

    lines.append("## Wplyw na poziomie zbiorow danych")
    lines.append("")
    for name in cat.assets:
        down = cat.downstream_assets(name)
        if down:
            lines.append(f"- Zmiana **`{name}`** wplywa na: " +
                         ", ".join(f"`{d}`" for d in down))
    lines.append("")

    lines.append("## Wplyw na poziomie kolumn")
    lines.append("")
    example_cols = [
        "weather_bronze.temperature",
        "weather_bronze.wind_speed",
        "weather_silver.humidity",
    ]
    for col in example_cols:
        down = cat.downstream_columns(col)
        if down:
            lines.append(f"- Zmiana **`{col}`** wplywa na kolumny: " +
                         ", ".join(f"`{d}`" for d in down))
        else:
            lines.append(f"- Zmiana **`{col}`** nie ma zarejestrowanych kolumn zaleznych.")
    lines.append("")

    path = out_dir / "impact_analysis.md"
    _write(path, "\n".join(lines))
    return path


def _esc(text: object) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _analytical_section() -> str:
    summary_path = config.REPORT_DIR / "station_summary.csv"
    if not summary_path.exists():
        return ""
    df = pd.read_csv(summary_path)

    rows = ""
    for _, r in df.iterrows():
        rows += (
            f"<tr><td><code>{_esc(r['station_id'])}</code></td>"
            f"<td>{_esc(r['hours_covered'])}</td>"
            f"<td>{_esc(r['avg_temperature'])}</td>"
            f"<td>{_esc(r['avg_comfort_index'])}</td>"
            f"<td>{_esc(r['total_rain_mm'])}</td>"
            f"<td>{_esc(r['peak_wind_speed'])}</td>"
            f"<td>{_esc(r['comfort_label'])}</td></tr>"
        )

    bars = ""
    for _, r in df.iterrows():
        width = max(0, min(100, float(r["avg_comfort_index"])))
        bars += (
            f'<div class="bar-row"><span class="bar-label">{_esc(r["station_id"])}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{width}%"></span></span>'
            f'<span class="bar-val">{_esc(r["avg_comfort_index"])}</span></div>'
        )

    warmest = df.loc[df["avg_temperature"].idxmax()]
    comfiest = df.loc[df["avg_comfort_index"].idxmax()]
    rainiest = df.loc[df["total_rain_mm"].idxmax()]
    windiest = df.loc[df["peak_wind_speed"].idxmax()]
    conclusions = (
        f"<li>Najcieplejsza stacja: <b>{_esc(warmest['station_id'])}</b> "
        f"({_esc(warmest['avg_temperature'])} stopni C srednio).</li>"
        f"<li>Najbardziej komfortowa stacja: <b>{_esc(comfiest['station_id'])}</b> "
        f"(wskaznik {_esc(comfiest['avg_comfort_index'])}, {_esc(comfiest['comfort_label'])}).</li>"
        f"<li>Najwiecej opadow: <b>{_esc(rainiest['station_id'])}</b> "
        f"({_esc(rainiest['total_rain_mm'])} mm lacznie).</li>"
        f"<li>Najsilniejszy wiatr: <b>{_esc(windiest['station_id'])}</b> "
        f"({_esc(windiest['peak_wind_speed'])} m/s w szczycie).</li>"
    )

    return f"""<section>
  <h2>Wyniki analityczne (per stacja)</h2>
  <table>
    <tr><th>Stacja</th><th>Godzin</th><th>Sr. temperatura</th><th>Sr. komfort</th>
        <th>Suma opadow (mm)</th><th>Maks. wiatr (m/s)</th><th>Ocena komfortu</th></tr>
    {rows}
  </table>
  <h3>Sredni wskaznik komfortu (0-100)</h3>
  <div class="chart">{bars}</div>
  <h3>Wnioski</h3>
  <ul>{conclusions}</ul>
</section>"""


def generate_html_report(cat: Catalog, out_dir: Path) -> Path:
    d = cat.to_dict()
    parts: list[str] = []

    parts.append("""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Katalog danych i lineage - Projekt 29</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });</script>
<style>
  body { font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 0; color: #1b1f24;
         background: #f6f8fa; }
  header { background: #0d1b2a; color: #fff; padding: 24px 32px; }
  header h1 { margin: 0 0 6px; font-size: 22px; }
  header .meta { color: #9fb3c8; font-size: 13px; }
  main { max-width: 1100px; margin: 0 auto; padding: 24px 32px 64px; }
  section { background: #fff; border: 1px solid #e1e4e8; border-radius: 10px;
            padding: 20px 24px; margin: 20px 0; }
  h2 { margin-top: 0; font-size: 18px; border-bottom: 2px solid #eaeef2; padding-bottom: 8px; }
  h3 { font-size: 15px; margin: 18px 0 8px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid #e1e4e8; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #f0f3f6; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px;
           color: #fff; }
  .bronze { background: #8a5a2b; } .silver { background: #6c757d; }
  .gold { background: #b8860b; } .report { background: #1f6feb; }
  code { background: #eef1f4; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
  .cards { display: flex; gap: 12px; flex-wrap: wrap; }
  .card { background: #f0f3f6; border-radius: 8px; padding: 12px 16px; min-width: 120px; }
  .card b { font-size: 20px; display: block; }
  .mermaid { background: #fbfdff; border: 1px dashed #c9d3de; border-radius: 8px; padding: 16px; }
  ul { margin: 6px 0; }
  .chart { margin: 8px 0; }
  .bar-row { display: flex; align-items: center; gap: 10px; margin: 4px 0; }
  .bar-label { width: 70px; font-size: 13px; font-family: monospace; }
  .bar-track { flex: 1; background: #eef1f4; border-radius: 6px; height: 18px; overflow: hidden; }
  .bar-fill { display: block; height: 100%; background: #1f6feb; }
  .bar-val { width: 48px; text-align: right; font-size: 13px; }
</style>
</head>
<body>
""")

    parts.append(f"""<header>
  <h1>Katalog danych i lineage</h1>
  <div class="meta">Projekt 29 &middot; uruchomienie <code>{_esc(cat.pipeline_run_id)}</code>
   &middot; wygenerowano {_esc(d['generated_at'])}</div>
</header>
<main>
""")

    n_cols = sum(len(a.columns) for a in cat.assets.values())
    parts.append(f"""<section>
  <h2>Podsumowanie</h2>
  <div class="cards">
    <div class="card"><b>{len(cat.assets)}</b>zbiory danych</div>
    <div class="card"><b>{len(cat.runs)}</b>uruchomienia</div>
    <div class="card"><b>{len(cat.edges)}</b>krawedzie zbiorow</div>
    <div class="card"><b>{len(cat.column_edges)}</b>krawedzie kolumn</div>
    <div class="card"><b>{n_cols}</b>skatalogowane kolumny</div>
  </div>
</section>""")

    parts.append(_analytical_section())

    parts.append(f"""<section>
  <h2>Lineage danych (pochodzenie)</h2>
  <pre class="mermaid">
{_esc(_mermaid_graph(cat))}
  </pre>
</section>""")

    parts.append('<section><h2>Katalog danych i schematy</h2>')
    for name, asset in sorted(cat.assets.items(),
                              key=lambda kv: (_LAYER_ORDER.get(kv[1].layer, 9), kv[0])):
        parts.append(
            f'<h3><code>{_esc(name)}</code> '
            f'<span class="badge {_esc(asset.layer)}">{_esc(asset.layer)}</span></h3>'
        )
        parts.append(f"<p>{_esc(asset.description)}</p>")
        parts.append(
            f"<p><small>Lokalizacja: <code>{_esc(asset.location)}</code> &middot; "
            f"format: {_esc(asset.fmt)} &middot; wierszy: {asset.row_count} &middot; "
            f"hash: <code>{_esc(asset.content_hash)}</code></small></p>"
        )
        parts.append("<table><tr><th>Kolumna</th><th>Typ</th><th>Dopuszcza puste</th>"
                     "<th>Liczba pustych</th><th>Pochodzi z</th><th>Opis</th></tr>")
        for c in asset.columns:
            src = "<br/>".join(_esc(s) for s in c.source_columns) if c.source_columns else "-"
            parts.append(
                f"<tr><td><code>{_esc(c.name)}</code></td><td>{_esc(c.dtype)}</td>"
                f"<td>{c.nullable}</td><td>{c.null_count}</td><td>{src}</td>"
                f"<td>{_esc(c.description)}</td></tr>"
            )
        parts.append("</table>")
    parts.append("</section>")

    parts.append('<section><h2>Dziennik uruchomien / transformacji</h2><table>'
                 '<tr><th>Uruchomienie</th><th>Krok</th><th>Status</th><th>Wejscia</th>'
                 '<th>Wyjscia</th><th>Metryki</th></tr>')
    for r in cat.runs:
        parts.append(
            f"<tr><td><code>{_esc(r.run_id)}</code></td><td>{_esc(r.step)}</td>"
            f"<td>{_esc(r.status)}</td><td>{_esc(', '.join(r.inputs))}</td>"
            f"<td>{_esc(', '.join(r.outputs))}</td><td>{_esc(r.metrics)}</td></tr>"
        )
    parts.append("</table></section>")

    parts.append('<section><h2>Analiza wplywu</h2>')
    parts.append("<h3>Na poziomie zbiorow danych</h3><ul>")
    for name in cat.assets:
        down = cat.downstream_assets(name)
        if down:
            parts.append(f"<li>Zmiana <code>{_esc(name)}</code> wplywa na: "
                         + ", ".join(f"<code>{_esc(x)}</code>" for x in down) + "</li>")
    parts.append("</ul><h3>Na poziomie kolumn (przyklady)</h3><ul>")
    for col in ["weather_bronze.temperature", "weather_bronze.wind_speed",
                "weather_silver.humidity"]:
        down = cat.downstream_columns(col)
        if down:
            parts.append(f"<li>Zmiana <code>{_esc(col)}</code> wplywa na: "
                         + ", ".join(f"<code>{_esc(x)}</code>" for x in down) + "</li>")
    parts.append("</ul></section>")

    parts.append("</main></body></html>")

    path = out_dir / "report.html"
    _write(path, "\n".join(parts))
    return path


def generate_all(cat: Catalog, out_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or config.DOCS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "html_report": generate_html_report(cat, out_dir),
        "data_catalog": generate_data_catalog(cat, out_dir),
        "lineage_mermaid": generate_lineage_mermaid(cat, out_dir),
        "impact_analysis": generate_impact_analysis(cat, out_dir),
        **dict(zip(
            ("lineage_edges", "column_lineage", "runs"),
            generate_lineage_tables(cat, out_dir),
        )),
    }
