"""Focused checks for real-source identifiers and leakage-safe rainfall windows."""

from datetime import date

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from scripts.build_real_dataset import _sample_negative_dates
from src.fetch_features import (	DISTRICT_NAMES,
	build_rainfall_features,
	load_selected_boundaries,
	verify_chirps_date_coverage,
)
from src.real_training import FEATURE_COLUMNS
from src.fetch_features import select_era5_points


def test_ifi_top_district_events_match_lgd_polygons_by_code():
	selected = {482: "Mumbai", 484: "Nagpur", 490: "Pune", 497: "Thane", 499: "Washim"}
	boundaries = load_selected_boundaries(codes=selected)
	assert {code: name for code, (name, _) in boundaries.items()} == selected
	assert all(geometry.is_valid for _, geometry in boundaries.values())

	events = pd.read_csv("data/real/ifi/India_Flood_Inventory_v3.csv")
	starts = pd.to_datetime(events["Start Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	eligible = events.loc[
		starts.notna()
		& starts.dt.year.between(2000, 2023)
		& starts.dt.month.between(6, 9)
	]
	counts = {code: 0 for code in selected}
	for _, row in eligible.iterrows():
		states = [part.strip() for part in str(row["State"]).split(",")]
		if states != ["Maharashtra"]:
			continue
		districts = [part.strip() for part in str(row["Districts"]).split(",")]
		codes = [part.strip() for part in str(row["District_LGD_Codes"]).split(",")]
		if len(districts) != len(codes):
			continue
		for district, code in set(zip(districts, codes)):
			if code in {str(value) for value in selected}:
				assert district == selected[int(code)]
				counts[int(code)] += 1
	assert counts == {482: 76, 484: 67, 490: 57, 497: 50, 499: 42}


def test_era5_selects_three_distinct_cells_per_district():
	for _, geometry in load_selected_boundaries().values():
		points, approximate = select_era5_points(geometry)
		assert len(points) == 3
		cells = {
			(
				round(round(latitude / 0.25) * 0.25, 6),
				round(round(longitude / 0.25) * 0.25, 6),
			)
			for latitude, longitude in points
		}
		assert len(cells) == 3
		if approximate:
			for index, (latitude, longitude) in enumerate(points):
				for other_latitude, other_longitude in points[index + 1:]:
					assert ((latitude - other_latitude) ** 2 + (longitude - other_longitude) ** 2) ** 0.5 > 0.375
		else:
			assert all(geometry.covers(Point(longitude, latitude)) for latitude, longitude in points)


def test_rainfall_features_use_only_days_before_observation():
	dates = pd.date_range("2020-01-02", "2020-02-01", freq="D")
	rain = pd.Series(0.0, index=dates)
	rain.loc["2020-01-30"] = 25.0
	rain.loc["2020-01-31"] = 4.0
	rain.loc["2020-02-01"] = 999.0

	features = build_rainfall_features(rain, [date(2020, 2, 1)]).iloc[0]
	assert features["rainfall_1d_total_mm"] == 4.0
	assert features["rainfall_1d_max_daily_mm"] == 4.0
	assert features["rainfall_3d_total_mm"] == 29.0
	assert features["rainfall_3d_max_daily_mm"] == 25.0
	assert features["days_since_rain_gt20mm"] == 2
	assert features["month"] == 2


def test_negative_sampling_excludes_padded_event_windows_and_matches_stratum():
	event_date = date(2000, 6, 10)
	blocked = {code: set() for code in DISTRICT_NAMES}
	blocked[482].update(
		date(2000, 6, day)
		for day in range(7, 14)
	)
	negative_dates, metadata = _sample_negative_dates(
		{(482, event_date): {"UEI-TEST"}},
		blocked,
		seed=7,
	)
	assert len(negative_dates) == 1
	code, sampled = negative_dates[0]
	assert code == 482
	assert (sampled.year, sampled.month) == (event_date.year, event_date.month)
	assert sampled not in blocked[code]
	assert metadata["negative_sampled"] == 1


def test_training_feature_list_excludes_target_and_split_identifiers():
	assert "flood_risk" not in FEATURE_COLUMNS
	assert "event_ueis" not in FEATURE_COLUMNS
	assert "date" not in FEATURE_COLUMNS
	assert "year" not in FEATURE_COLUMNS
	assert "district" in FEATURE_COLUMNS
	assert "month" in FEATURE_COLUMNS


class _FakeResponse:
	text = "time\nUTC\n2000-06-01T00:00:00Z\n2000-06-03T00:00:00Z\n"

	@staticmethod
	def raise_for_status():
		return None


class _FakeSession:
	def __init__(self):
		self.url = None

	def get(self, url, timeout):
		self.url = url
		return _FakeResponse()


def test_chirps_date_coverage_rejects_missing_daily_sample():
	session = _FakeSession()
	with pytest.raises(ValueError, match="missing days by year=.*2000.*1"):
		verify_chirps_date_coverage(date(2000, 6, 1), date(2000, 6, 3), session=session)
	assert "chirps20GlobalDailyP05.csv" in session.url