# Global CO₂ Analysis

Interactive charts of annual emissions, the top ten emitting countries and
territories, and emissions per person. The committed report covers **2022**,
with selected-country trends from **1990 to 2022**.

## View the report

From the repository directory:

```sh
python -m http.server 8000
```

Open http://localhost:8000. Both `index.html` and the existing `Global.html`
entry point work. Charts share a versioned Plotly CDN script instead of
embedding several megabytes in each file. Viewing charts requires an internet
connection for that script and map geographic assets.

## Install and reproduce

Use Python 3.11 or 3.12:

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python Global.py
```

The default input is the OWID CSV at commit
[`382ee6c662b0ece26e111f263b44c029afad7787`](https://github.com/owid/co2-data/tree/382ee6c662b0ece26e111f263b44c029afad7787).
A pinned revision avoids silently changing the results when upstream data are
updated. The first/default run requires internet access for that CSV. Results
are written beside the script, regardless of your working directory.

Customise the period, countries or destination:

```sh
python Global.py --year 2021 --start-year 2000 --countries "United Kingdom" "China" --output-dir output
python Global.py --input /path/to/owid-co2-data.csv --year 2022 --output-dir output
```

`--year` must exist in the input and be at least `--start-year`. The supplied
country names select the line-chart series; the ranking and map still consider
all eligible countries/territories. Unavailable line-chart countries are omitted
and the included names are recorded in the metadata; an entirely empty
selection fails with a clear error. Local CSV input allows offline generation; viewing the charts still needs internet access.

## Method and limitations

- Country/territory rows must have an ISO 3166-1 alpha-3 code recognised by the
  pinned `pycountry` version. This excludes world, regional and income-group
  aggregates, historical entities and locations without assigned ISO codes.
  The rule includes territories and is not a sovereignty classification.
- Rank by annual `co2`, descending, for the selected year. A country-name
  tie-breaker makes equal values deterministic. Show up to ten available rows.
- A missing per-capita value does **not** remove valid total emissions from the
  ranking. Each chart drops rows only for the metric it uses. Missing values
  are never treated as zero. Population is not required by this analysis.
- Schema, numeric/year values and duplicate country/year rows are validated.
- The line chart sorts years chronologically and uses an inclusive year range.
- Annual emissions are shown in million tonnes (Mt); per-capita values are
  tonnes per person. Missing years/data and territorial definitions limit direct
  comparisons. A current ISO list can exclude historical entities in older periods.

## Outputs

| File | Contents |
| --- | --- |
| `index.html`, `Global.html` | Accessible landing page with chart descriptions and source attribution |
| `line_chart.html` | Selected-country annual emissions |
| `bar_chart.html` | Country/territory ranking, excluding aggregates |
| `map_chart.html` | Per-capita emissions located by ISO code |
| `top_emitters.csv` | The plotted ranking for inspection/reuse |
| `analysis_metadata.json` | Input URL/path, SHA-256, settings, included countries and package versions |

Figures use stable element IDs, so repeated runs with the same input and
software do not introduce random chart IDs. Direct dependencies are pinned;
metadata records the core package versions used. This is not a complete
cross-platform environment lock.

## Tests

```sh
python -m unittest discover -s tests -v
```

The tests use small synthetic fixtures, without contacting OWID. They cover
aggregate exclusion, missing values, year/country filters, ranking limits,
invalid data and generation of a complete report. GitHub Actions runs them
on Python 3.11 and 3.12.

## Data attribution

Data: [Our World in Data CO₂ dataset](https://github.com/owid/co2-data).
See its [README](https://github.com/owid/co2-data/blob/382ee6c662b0ece26e111f263b44c029afad7787/README.md)
and [codebook](https://github.com/owid/co2-data/blob/382ee6c662b0ece26e111f263b44c029afad7787/owid-co2-codebook.csv)
for variable definitions, original providers and applicable reuse terms. The
metadata records the precise source used; this project does not claim ownership
of the underlying data.
