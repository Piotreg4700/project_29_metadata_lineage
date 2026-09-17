from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from src.catalog import Catalog

_LAYER_ORDER = {"bronze": 0, "silver": 1, "gold": 2, "report": 3}


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _esc(text: object) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _mermaid_graph(cat: Catalog) -> str:
    lines = ["graph LR"]
    lines.append('  weather_api["weather_api (REST)"]')
    for name, asset in cat.assets.items():
        lines.append(f'  {name}["{name}<br/>({asset.layer}, {asset.row_count} wierszy)"]')
    for e in cat.edges:
        lines.append(f"  {e.src} --> {e.dst}")
    return "\n".join(lines)


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


def generate_html_report(cat: Catalog, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or config.DOCS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
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
   &middot; wygenerowano {_esc(cat.generated_at)}</div>
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
