"""tests/test_regions.py

Unit tests for pipeline.features.regions.assign_region_by_latlon.
"""

import json

import pandas as pd

from pipeline.features.regions import assign_region_by_latlon
from pipeline.model import regional_scoring


class TestAssignRegionByLatLon:
    def test_caribbean(self):
        assert assign_region_by_latlon(15, -70) == "Caribbean"

    def test_caribbean_takes_precedence_over_americas_pacific(self):
        # This cell sits inside both the Caribbean and Americas Pacific boxes;
        # Caribbean must win since it's checked first.
        assert assign_region_by_latlon(15, -70) == "Caribbean"

    def test_americas_pacific(self):
        # Chile coast — inside Americas Pacific, outside the Caribbean box.
        assert assign_region_by_latlon(-30, -70) == "Americas Pacific"

    def test_middle_east(self):
        assert assign_region_by_latlon(25, 45) == "Middle East"

    def test_middle_east_takes_precedence_in_mediterranean_overlap(self):
        # lat 35 / lon 35 falls in both the Mediterranean and Middle East
        # boxes; Middle East must win since it's checked first.
        assert assign_region_by_latlon(35, 35) == "Middle East"

    def test_mediterranean(self):
        # Italy — inside Mediterranean, outside the Middle East box.
        assert assign_region_by_latlon(40, 10) == "Mediterranean"

    def test_south_asia(self):
        assert assign_region_by_latlon(20, 75) == "South Asia"

    def test_pacific_ring_asia_oceania(self):
        # Japan
        assert assign_region_by_latlon(35, 140) == "Pacific Ring Asia/Oceania"

    def test_unclassified(self):
        # Antarctica interior — matches no box.
        assert assign_region_by_latlon(-80, 0) == "Unclassified"


class TestRegionalScoring:
    def test_score_region_uses_one_highest_risk_prediction_per_month(self):
        rows = [
            {"date": "2000-01-01", "EQIndicator": 0, "risk_score": 0.20},
            {"date": "2000-01-10", "EQIndicator": 1, "risk_score": 0.90},
            {"date": "2000-02-01", "EQIndicator": 0, "risk_score": 0.95},
            {"date": "2000-02-20", "EQIndicator": 1, "risk_score": 0.10},
        ]

        result = regional_scoring.score_region(
            pd.DataFrame(rows),
            "Fixture",
            window_days=2,
        )

        assert result["n_predictions"] == 2
        assert result["hits"] == 1
        assert result["hit_rate"] == 0.5
        # Two event-backed 7-day candidate windows over 54 complete 7-day starts:
        # Jan 4-10, Jan 5-11, Jan 6-12, Jan 7-13, Jan 8-14, Jan 9-15, Jan 10-16
        # and Feb 14-20, Feb 15-21, Feb 16-22, Feb 17-23, Feb 18-24, Feb 19-25, Feb 20-26.
        assert result["base_rate"] == 0.2593
        assert result["lift"] == 1.9286

    def test_score_region_handles_empty_subset(self):
        result = regional_scoring.score_region(
            pd.DataFrame(columns=["date", "EQIndicator", "risk_score"]),
            "Missing",
        )

        assert result == {
            "region": "Missing",
            "n_predictions": 0,
            "hits": 0,
            "hit_rate": 0.0,
            "base_rate": 0.0,
            "lift": None,
            "p_value": None,
        }

    def test_main_writes_mexico_peru_chile_results(self, monkeypatch, tmp_path):
        rows = []
        for country in ["Mexico", "Peru", "Chile"]:
            rows.extend(
                [
                    {
                        "date": "2000-01-01",
                        "EQIndicator": 0,
                        "risk_score": 0.10,
                        "country": country,
                        "region": "Unclassified",
                    },
                    {
                        "date": "2000-01-05",
                        "EQIndicator": 1,
                        "risk_score": 0.90,
                        "country": country,
                        "region": "Unclassified",
                    },
                ]
            )

        output_path = tmp_path / "regional_validation_extended.json"
        monkeypatch.setattr(
            regional_scoring.pd,
            "read_parquet",
            lambda path: pd.DataFrame(rows),
        )
        monkeypatch.setattr(regional_scoring, "OUTPUT_PATH", str(output_path))

        results = regional_scoring.main()

        names = {r["region"] for r in results}
        assert {"Mexico", "Peru", "Chile"}.issubset(names)
        written_names = {r["region"] for r in json.loads(output_path.read_text())}
        assert {"Mexico", "Peru", "Chile"}.issubset(written_names)
