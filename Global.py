"""Generate country-only CO2 charts from a versioned OWID dataset or local CSV."""

import argparse
import hashlib
from html import escape
import io
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import pycountry

DATA_COMMIT = "382ee6c662b0ece26e111f263b44c029afad7787"
DEFAULT_SOURCE = f"https://raw.githubusercontent.com/owid/co2-data/{DATA_COMMIT}/owid-co2-data.csv"
DEFAULT_COUNTRIES = ["United States", "China", "India", "Germany", "Brazil"]
REQUIRED = {"country", "iso_code", "year", "co2", "co2_per_capita"}
ISO_CODES = frozenset(country.alpha_3 for country in pycountry.countries)


def load_data(source):
    """Return validated data and provenance; do not download on module import."""
    if str(source).startswith("https://"):
        with urlopen(str(source), timeout=60) as response:
            raw = response.read()
    else:
        raw = Path(source).read_bytes()
    frame = validate_data(pd.read_csv(io.BytesIO(raw)))
    return frame, {"source": str(source), "source_sha256": hashlib.sha256(raw).hexdigest()}


def validate_data(frame):
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    frame = frame.copy()
    if frame["country"].isna().any() or frame["country"].astype(str).str.strip().eq("").any():
        raise ValueError("Country names must not be blank")
    for column in ["year", "co2", "co2_per_capita"]:
        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except (ValueError, TypeError) as error:
            raise ValueError(f"Column {column} must contain numbers or missing values") from error
        if np.isinf(frame[column].dropna()).any():
            raise ValueError(f"Column {column} contains infinite values")
    if frame["year"].isna().any() or frame["year"].mod(1).ne(0).any():
        raise ValueError("Year must contain whole numbers without missing values")
    frame["year"] = frame["year"].astype(int)
    countries = frame[frame["iso_code"].isin(ISO_CODES)]
    if countries.duplicated(["iso_code", "year"]).any():
        raise ValueError("Duplicate country/year rows; resolve duplicates before ranking")
    return frame


def select_data(frame, year=2022, start_year=1990, countries=None):
    """Exclude aggregates, then drop missing values independently per chart."""
    if start_year > year:
        raise ValueError("Start year must not exceed the analysis year")
    frame = validate_data(frame)
    national = frame[frame["iso_code"].isin(ISO_CODES)].copy()
    national = national[national["year"].between(start_year, year)]
    annual = national[national["year"].eq(year)]
    ranking = annual.dropna(subset=["co2"]).sort_values(
        ["co2", "country"], ascending=[False, True]
    ).head(10)
    world_map = annual.dropna(subset=["co2_per_capita"]).sort_values("iso_code")
    names = DEFAULT_COUNTRIES if countries is None else countries
    line = national[national["country"].isin(names)].dropna(subset=["co2"])
    line = line.sort_values(["country", "year"])
    if ranking.empty:
        raise ValueError(f"No country emissions are available for {year}")
    if world_map.empty:
        raise ValueError(f"No country per-capita emissions are available for {year}")
    if line.empty:
        raise ValueError("No emissions match the selected countries and year range")
    return line, ranking, world_map


def dashboard_html(year, start_year, count, source):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Global CO₂ Analysis — {year}</title>
  <style>
    body {{ font: 1rem/1.6 system-ui, sans-serif; max-width: 1100px; margin: auto; padding: 1.5rem; color: #172033; background: #f5f7fb; overflow-wrap: anywhere; }}
    a {{ color: #144bb8; }}
    iframe {{ width: 100%; height: 570px; border: 1px solid #d5dbe5; background: white; border-radius: 8px; }}
    .note {{ background: #e5edfb; padding: 1rem; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>Global CO₂ Analysis — {year}</h1>
  <p>Country and territory emissions from Our World in Data, {start_year}–{year}.</p>
  <p class="note">Rankings use ISO 3166-1 country/territory codes and exclude world, regional and income-group totals.
  Missing values are omitted per chart, never replaced with zero. Historical entities and places without an assigned ISO code are excluded.</p>
  <h2>Emissions over time for selected countries</h2>
  <iframe src="line_chart.html" title="Annual CO2 emissions by selected country"></iframe>
  <h2>Top {count} emitting countries and territories in {year}</h2>
  <iframe src="bar_chart.html" title="Country emissions ranking for {year}" loading="lazy"></iframe>
  <h2>CO₂ emissions per capita in {year}</h2>
  <iframe src="map_chart.html" title="World map of per-capita CO2 emissions in {year}" loading="lazy"></iframe>
  <p>Annual CO₂: million tonnes (Mt). Per-capita CO₂: tonnes per person. See the
  <a href="https://github.com/owid/co2-data">OWID dataset documentation</a> for definitions and original source attribution.</p>
  <p>Data input: {escape(source)}. <a href="analysis_metadata.json">Reproduction metadata</a> ·
  <a href="top_emitters.csv">Download ranking CSV</a> · <a href="https://github.com/ian-Wu2023/Global-Co2-Analysis">Source code</a></p>
  <p>Charts load a versioned Plotly script and map geographic assets from the internet.</p>
</body>
</html>
'''


def generate_report(frame, output_dir, year=2022, start_year=1990, countries=None, provenance=None):
    line, ranking, world_map = select_data(frame, year, start_year, countries)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    provenance = provenance or {"source": "in-memory data"}
    figures = {
        "line_chart.html": px.line(line, x="year", y="co2", color="country",
                                  title=f"CO₂ emissions, {start_year}–{year}",
                                  labels={"co2": "CO₂ emissions (Mt)", "year": "Year", "country": "Country / territory"}),
        "bar_chart.html": px.bar(ranking, x="country", y="co2", text="co2",
                                title=f"Top {len(ranking)} emitting countries and territories in {year}",
                                labels={"co2": "CO₂ emissions (Mt)", "country": "Country / territory"}),
        "map_chart.html": px.choropleth(world_map, locations="iso_code", locationmode="ISO-3",
                                       hover_name="country", color="co2_per_capita",
                                       title=f"CO₂ emissions per capita ({year})",
                                       color_continuous_scale="Viridis",
                                       labels={"co2_per_capita": "CO₂ per capita (tonnes)"}),
    }
    figures["bar_chart.html"].update_traces(texttemplate="%{text:.3s}", textposition="outside", cliponaxis=False)
    for name, figure in figures.items():
        figure.update_layout(template="plotly_white", margin=dict(t=80, b=90))
        figure.write_html(output / name, include_plotlyjs="cdn", full_html=True,
                          div_id=name.removesuffix(".html"), config={"responsive": True})
    ranking[["country", "iso_code", "year", "co2"]].to_csv(output / "top_emitters.csv", index=False)
    metadata = {
        **provenance,
        "analysis_year": year,
        "start_year": start_year,
        "country_rule": "ISO 3166-1 alpha-3 membership; includes territories, excludes aggregates and unassigned codes",
        "requested_line_countries": DEFAULT_COUNTRIES if countries is None else countries,
        "line_countries_with_data": sorted(line["country"].unique().tolist()),
        "ranking_countries": ranking["country"].tolist(),
        "map_country_count": len(world_map),
        "versions": {"pandas": pd.__version__, "numpy": np.__version__, "plotly": plotly.__version__, "pycountry": pycountry.__version__},
    }
    (output / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    html = dashboard_html(year, start_year, len(ranking), provenance["source"])
    for name in ["index.html", "Global.html"]:
        (output / name).write_text(html, encoding="utf-8")
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_SOURCE, help="Local CSV or HTTPS URL; defaults to a pinned OWID revision")
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--start-year", type=int, default=1990)
    parser.add_argument("--countries", nargs="+", default=DEFAULT_COUNTRIES, help="Country names for the line chart")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    try:
        frame, provenance = load_data(args.input)
        generate_report(frame, args.output_dir, args.year, args.start_year, args.countries, provenance)
    except (ValueError, OSError) as error:
        parser.exit(1, f"CO₂ analysis failed: {error}\n")
    print(f"Report saved to {args.output_dir.resolve() / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
