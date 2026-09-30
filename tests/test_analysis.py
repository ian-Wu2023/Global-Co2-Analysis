"""Offline regression tests for country rankings and report generation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from Global import generate_report, load_data, main, select_data, validate_data


def sample():
    return pd.DataFrame([
        ["World", "OWID_WRL", 2022, 50000, 6],
        ["Asia", None, 2022, 30000, 5],
        ["High-income countries", "OWID_HIC", 2022, 20000, 9],
        ["Unknown entity", "ZZZ", 2022, 19000, 8],
        ["China", "CHN", 2022, 10000, 7],
        ["United States", "USA", 2022, 5000, None],
        ["India", "IND", 2022, None, 2],
        ["Germany", "DEU", 2022, 700, 8],
        ["China", "CHN", 2021, 9000, 6.5],
        ["United States", "USA", 2021, 4000, 12],
        ["China", "CHN", 1989, 2000, 2],
        ["China", "CHN", 2023, 11000, 8],
    ], columns=["country", "iso_code", "year", "co2", "co2_per_capita"])


class AnalysisTests(unittest.TestCase):
    def test_ranking_excludes_aggregates_and_unknown_codes(self):
        _, ranking, _ = select_data(sample())
        self.assertEqual(ranking.country.tolist(), ["China", "United States", "Germany"])

    def test_missing_values_are_dropped_only_for_relevant_metric(self):
        line, ranking, world_map = select_data(sample())
        self.assertIn("United States", ranking.country.tolist())
        self.assertIn("United States", line.country.tolist())
        self.assertNotIn("United States", world_map.country.tolist())
        self.assertIn("India", world_map.country.tolist())
        self.assertNotIn("India", ranking.country.tolist())

    def test_missing_population_does_not_change_rankings(self):
        data = sample().assign(population=float("nan"))
        self.assertEqual(select_data(data)[1].country.tolist(), ["China", "United States", "Germany"])

    def test_year_range_and_selected_countries(self):
        line, ranking, _ = select_data(sample(), year=2021, start_year=2020, countries=["China"])
        self.assertEqual(line.country.tolist(), ["China"])
        self.assertEqual(line.year.tolist(), [2021])
        self.assertEqual(ranking.year.unique().tolist(), [2021])

    def test_rankings_are_limited_to_ten(self):
        codes = ["GBR", "FRA", "DEU", "ITA", "ESP", "PRT", "USA", "CAN", "CHN", "IND", "BRA", "JPN"]
        frame = pd.DataFrame([[code, code, 2022, i, 1] for i, code in enumerate(codes)], columns=sample().columns)
        _, ranking, _ = select_data(frame, countries=codes)
        self.assertEqual(len(ranking), 10)
        self.assertEqual(ranking.co2.tolist(), list(range(11, 1, -1)))

    def test_duplicate_country_year_rejected(self):
        data = pd.concat([sample(), sample().iloc[[4]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_data(data)

    def test_missing_required_column_rejected(self):
        with self.assertRaisesRegex(ValueError, "iso_code"):
            validate_data(sample().drop(columns="iso_code"))

    def test_bad_numeric_values_rejected(self):
        for value in ["broken", float("inf")]:
            with self.subTest(value=value):
                data = sample().astype({"co2": object})
                data.loc[4, "co2"] = value
                with self.assertRaises(ValueError):
                    validate_data(data)

    def test_invalid_year_values_rejected(self):
        for value in [None, 2022.5]:
            with self.subTest(value=value):
                data = sample().astype({"year": float})
                data.loc[4, "year"] = value
                with self.assertRaisesRegex(ValueError, "Year"):
                    validate_data(data)

    def test_unavailable_year_or_countries_have_clear_errors(self):
        for kwargs, message in [({"year": 1980}, "Start year"), ({"year": 2030}, "No country emissions"),
                                ({"countries": ["Missing"]}, "selected countries")]:
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, message):
                select_data(sample(), **kwargs)

    def test_local_input_and_generated_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.csv"
            sample().to_csv(source, index=False)
            frame, provenance = load_data(source)
            self.assertEqual(len(provenance["source_sha256"]), 64)
            report = root / "report"
            metadata = generate_report(frame, report, year=2021, start_year=2020, provenance=provenance)
            self.assertEqual(metadata["ranking_countries"], ["China", "United States"])
            for name in ["index.html", "Global.html", "line_chart.html", "bar_chart.html", "map_chart.html",
                         "top_emitters.csv", "analysis_metadata.json"]:
                self.assertTrue((report / name).is_file(), name)
            self.assertEqual((report / "index.html").read_text(), (report / "Global.html").read_text())
            self.assertIn("Top 2 emitting countries and territories in 2021", (report / "index.html").read_text())
            self.assertIn('https://cdn.plot.ly/plotly-', (report / "bar_chart.html").read_text())
            self.assertEqual(json.loads((report / "analysis_metadata.json").read_text())["analysis_year"], 2021)

    def test_cli_failure_returns_nonzero(self):
        with patch("Global.load_data", side_effect=ValueError("Missing required columns: iso_code")):
            with self.assertRaises(SystemExit) as error:
                main(["--input", "missing-column.csv"])
            self.assertEqual(error.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
