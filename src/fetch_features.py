"""Fetch and aggregate bounded CHIRPS rainfall for selected LGD districts."""

import argparse
import json
import logging
import math
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
import time
from typing import Any

import numpy as np
import pandas as pd
import requests
import xarray as xr
from shapely import contains_xy, wkb
from shapely.geometry import Point

from src.config import ROOT_DIR

logger = logging.getLogger(__name__)

CHIRPS_DATASET_ID = "chirps20GlobalDailyP05"
CHIRPS_ERDDAP_URL = "https://coastwatch.pfeg.noaa.gov/erddap"
CHIRPS_GRID_RESOLUTION = 0.05
CHIRPS_GRID_ORIGIN = 0.025
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ERA5_MODEL = "era5"
ERA5_GRID_RESOLUTION = 0.25
ERA5_RETRIES = 7
ERA5_REQUEST_SPACING_SECONDS = 0.5
ERA5_CACHE_DIR = ROOT_DIR / "data/real/era5"
DEFAULT_BOUNDARY_PATH = ROOT_DIR / "data/real/boundaries/LGD_Districts.parquet"
DEFAULT_CACHE_DIR = ROOT_DIR / "data/real/chirps"
DEFAULT_START_DATE = date(2000, 5, 2)
DEFAULT_END_DATE = date(2023, 9, 29)
MAX_CHUNK_DAYS = 365
DISTRICT_NAMES = {482: "Mumbai", 484: "Nagpur", 490: "Pune", 497: "Thane", 499: "Washim"}


def verify_chirps_dataset(session: requests.Session | None = None) -> dict[str, Any]:
	"""Verify the NOAA ERDDAP dataset and precipitation units before any download."""
	client = session or requests.Session()
	url = f"{CHIRPS_ERDDAP_URL}/info/{CHIRPS_DATASET_ID}/index.json"
	response = client.get(url, timeout=(15, 60))
	response.raise_for_status()
	table = response.json().get("table", {})
	rows = table.get("rows", [])
	precip_variable = next(
		(row for row in rows if row[:2] == ["variable", "precip"]), None
	)
	precip_units = next(
		(
			row[4]
			for row in rows
			if row[:3] == ["attribute", "precip", "units"]
		),
		None,
	)
	if precip_variable is None or precip_units != "mm/day":
		raise ValueError(
		f"Unexpected CHIRPS metadata at {url}: precip={precip_variable}, units={precip_units}."
		)
	return {"dataset_id": CHIRPS_DATASET_ID, "info_url": url, "precip_units": precip_units}


def verify_chirps_date_coverage(
	start_date: date,
	end_date: date,
	session: requests.Session | None = None,
) -> pd.DatetimeIndex:
	"""Require a true daily time coordinate for every requested date."""
	if end_date < start_date:
		raise ValueError("end_date must be on or after start_date.")
	url = (
		f"{CHIRPS_ERDDAP_URL}/griddap/{CHIRPS_DATASET_ID}.csv?"
		f"time[({start_date.isoformat()}T00:00:00Z):1:({end_date.isoformat()}T00:00:00Z)]"
	)
	client = session or requests.Session()
	response = client.get(url, timeout=(15, 120))
	response.raise_for_status()
	frame = pd.read_csv(StringIO(response.text), comment="#")
	if "time" not in frame:
		raise ValueError(f"CHIRPS time-coordinate response has no 'time' column: {url}")
	available = pd.DatetimeIndex(
		pd.to_datetime(frame["time"], format="ISO8601", errors="coerce", utc=True).dropna()
	).normalize().unique().sort_values()
	expected = pd.date_range(start_date, end_date, freq="D", tz="UTC")
	missing = expected.difference(available)
	if len(missing):
		missing_by_year = {
			str(year): int(sum(timestamp.year == year for timestamp in missing))
			for year in sorted({timestamp.year for timestamp in missing})
		}
		raise ValueError(
			"NOAA ERDDAP CHIRPS time axis is incomplete for the requested period: "
			f"{len(available)} of {len(expected)} daily records available; "
			f"missing days by year={missing_by_year}. No rainfall cache was created."
		)
	return available


def load_selected_boundaries(
	boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
	codes: Iterable[int] = DISTRICT_NAMES,
) -> dict[int, tuple[str, Any]]:
	"""Load valid district polygons by exact LGD code, never by district name."""
	path = Path(boundary_path)
	if not path.is_file():
		raise FileNotFoundError(f"LGD district boundaries not found: {path}")
	frame = pd.read_parquet(path, columns=["dist_lgd", "dtname", "stname", "geometry"])
	selected: dict[int, tuple[str, Any]] = {}
	for code in codes:
		rows = frame.loc[frame["dist_lgd"].astype("int64") == int(code)]
		if len(rows) != 1:
			raise ValueError(f"Expected one LGD boundary for code {code}; found {len(rows)}.")
		row = rows.iloc[0]
		if str(row["stname"]).strip().upper() != "MAHARASHTRA":
			raise ValueError(f"LGD code {code} is not in Maharashtra: {row['stname']}.")
		geometry = wkb.loads(row["geometry"])
		if geometry.is_empty or not geometry.is_valid:
			raise ValueError(f"LGD boundary {code} ({row['dtname']}) has invalid geometry.")
		selected[int(code)] = (str(row["dtname"]), geometry)
	return selected


def _snap_grid(value: float, lower: bool) -> float:
	index = (value - CHIRPS_GRID_ORIGIN) / CHIRPS_GRID_RESOLUTION
	grid_index = math.floor(index + 1e-9) if lower else math.ceil(index - 1e-9)
	return round(CHIRPS_GRID_ORIGIN + grid_index * CHIRPS_GRID_RESOLUTION, 3)


def district_grid_bounds(geometry: Any) -> tuple[float, float, float, float]:
	"""Return a minimal CHIRPS grid-center rectangle covering a district polygon."""
	min_lon, min_lat, max_lon, max_lat = geometry.bounds
	return (
		_snap_grid(min_lon, lower=True),
		_snap_grid(min_lat, lower=True),
		_snap_grid(max_lon, lower=False),
		_snap_grid(max_lat, lower=False),
	)


def build_chirps_subset_url(
	geometry: Any,
	start_date: date,
	end_date: date,
) -> str:
	"""Build an ERDDAP NetCDF request constrained to a district bbox and dates."""
	if end_date < start_date:
		raise ValueError("end_date must be on or after start_date.")
	min_lon, min_lat, max_lon, max_lat = district_grid_bounds(geometry)
	start = f"{start_date.isoformat()}T00:00:00Z"
	end = f"{end_date.isoformat()}T00:00:00Z"
	query = (
		f"precip[({start}):1:({end})]"
		f"[({min_lat:.3f}):1:({max_lat:.3f})]"
		f"[({min_lon:.3f}):1:({max_lon:.3f})]"
	)
	return f"{CHIRPS_ERDDAP_URL}/griddap/{CHIRPS_DATASET_ID}.nc?{query}"


def _validate_netcdf(
	path: Path,
	start_date: date,
	end_date: date,
	geometry: Any,
) -> None:
	with xr.open_dataset(path, engine="netcdf4") as dataset:
		if "precip" not in dataset or not {"time", "latitude", "longitude"}.issubset(
			dataset["precip"].dims
		):
			raise ValueError(f"Unexpected CHIRPS NetCDF schema in {path}.")
		if dataset["precip"].attrs.get("units") != "mm/day":
			raise ValueError(f"CHIRPS precipitation units are not mm/day in {path}.")
		times = pd.to_datetime(dataset["time"].values)
		if times.min().date() != start_date or times.max().date() != end_date:
			raise ValueError(f"CHIRPS date extent in {path} does not match the request.")
		longitude, latitude = np.meshgrid(dataset["longitude"].values, dataset["latitude"].values)
		if not contains_xy(geometry, longitude, latitude).any():
			raise ValueError(f"No CHIRPS grid centers fall inside district geometry in {path}.")


def download_district_chirps(
	code: int,
	geometry: Any,
	start_date: date = DEFAULT_START_DATE,
	end_date: date = DEFAULT_END_DATE,
	cache_dir: str | Path = DEFAULT_CACHE_DIR,
	force: bool = False,
	session: requests.Session | None = None,
) -> Path:
	"""Download one bounded district/date subset to a local NetCDF cache."""
	cache = Path(cache_dir)
	cache.mkdir(parents=True, exist_ok=True)
	path = cache / f"chirps_lgd_{int(code)}_{start_date.isoformat()}_{end_date.isoformat()}.nc"
	if path.exists() and not force:
		_validate_netcdf(path, start_date, end_date, geometry)
		return path
	url = build_chirps_subset_url(geometry, start_date, end_date)
	logger.info("Downloading LGD %s CHIRPS subset: %s", code, url)
	client = session or requests.Session()
	temporary_path = path.with_suffix(path.suffix + ".part")
	try:
		with client.get(url, stream=True, timeout=(20, 300)) as response:
			response.raise_for_status()
			with temporary_path.open("wb") as output:
				for block in response.iter_content(chunk_size=1024 * 1024):
					if block:
						output.write(block)
		_validate_netcdf(temporary_path, start_date, end_date, geometry)
		temporary_path.replace(path)
	except Exception:
		temporary_path.unlink(missing_ok=True)
		raise
	return path


def _date_chunks(start_date: date, end_date: date) -> list[tuple[date, date]]:
	"""Split a request into annual-sized chunks accepted by the public ERDDAP server."""
	chunks: list[tuple[date, date]] = []
	chunk_start = start_date
	while chunk_start <= end_date:
		chunk_end = min(end_date, chunk_start + timedelta(days=MAX_CHUNK_DAYS - 1))
		chunks.append((chunk_start, chunk_end))
		chunk_start = chunk_end + timedelta(days=1)
	return chunks


def district_daily_rainfall(
	path: str | Path,
	geometry: Any,
) -> pd.Series:
	"""Average valid CHIRPS grid-cell centers contained by an LGD polygon."""
	with xr.open_dataset(path, engine="netcdf4") as dataset:
		precipitation = dataset["precip"].transpose("time", "latitude", "longitude")
		longitudes, latitudes = np.meshgrid(
			dataset["longitude"].values, dataset["latitude"].values
		)
		inside = contains_xy(geometry, longitudes, latitudes)
		if not inside.any():
			raise ValueError(f"No CHIRPS grid centers inside polygon for {path}.")
		values = np.asarray(precipitation.values, dtype=np.float64)
		selected = values[:, inside]
		valid = np.isfinite(selected)
		counts = valid.sum(axis=1)
		totals = np.where(valid, selected, 0.0).sum(axis=1)
		daily_mean = np.divide(
			totals,
			counts,
			out=np.full_like(totals, np.nan, dtype=np.float64),
			where=counts > 0,
		)
		index = pd.DatetimeIndex(pd.to_datetime(dataset["time"].values)).normalize()
	return pd.Series(daily_mean, index=index, name="district_rainfall_mm").sort_index()


def build_rainfall_features(
	daily_rainfall: pd.Series,
	observation_dates: Iterable[pd.Timestamp | date | str],
) -> pd.DataFrame:
	"""Build rainfall windows ending on the day before each observation date."""
	series = daily_rainfall.copy().sort_index()
	series.index = pd.DatetimeIndex(series.index).normalize()
	if series.index.has_duplicates:
		series = series.groupby(level=0).mean()
	rows: list[dict[str, Any]] = []
	for value in observation_dates:
		observation_date = pd.Timestamp(value).normalize()
		window_end = observation_date - pd.Timedelta(days=1)
		row: dict[str, Any] = {"date": observation_date, "month": int(observation_date.month)}
		for days in (1, 3, 7, 14, 30):
			window_start = observation_date - pd.Timedelta(days=days)
			window = series.loc[window_start:window_end]
			if len(window) != days:
				row[f"rainfall_{days}d_total_mm"] = np.nan
				row[f"rainfall_{days}d_max_daily_mm"] = np.nan
			elif window.isna().any():
				row[f"rainfall_{days}d_total_mm"] = np.nan
				row[f"rainfall_{days}d_max_daily_mm"] = np.nan
			else:
				row[f"rainfall_{days}d_total_mm"] = float(window.sum())
				row[f"rainfall_{days}d_max_daily_mm"] = float(window.max())
		historical_rain = series.loc[:window_end]
		heavy_rain_days = historical_rain[historical_rain > 20].index
		row["days_since_rain_gt20mm"] = (
			int((observation_date - heavy_rain_days[-1]).days)
			if len(heavy_rain_days)
			else np.nan
		)
		rows.append(row)
	return pd.DataFrame(rows)


def fetch_chirps_subsets(
	codes: Iterable[int] = DISTRICT_NAMES,
	start_date: date = DEFAULT_START_DATE,
	end_date: date = DEFAULT_END_DATE,
	boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
	cache_dir: str | Path = DEFAULT_CACHE_DIR,
	force: bool = False,
) -> dict[int, list[Path]]:
	"""Verify the ERDDAP source and cache each selected district's bounded slice."""
	verify_chirps_dataset()
	verify_chirps_date_coverage(start_date, end_date)
	boundaries = load_selected_boundaries(boundary_path, codes)
	return {
		code: [
			download_district_chirps(
				code,
				geometry,
				chunk_start,
				chunk_end,
				cache_dir=cache_dir,
				force=force,
			)
			for chunk_start, chunk_end in _date_chunks(start_date, end_date)
		]
		for code, (_, geometry) in boundaries.items()
	}


def _regular_grid_values(minimum: float, maximum: float) -> list[float]:
	step = ERA5_GRID_RESOLUTION
	first = math.ceil((minimum - 1e-9) / step) * step
	last = math.floor((maximum + 1e-9) / step) * step
	if last < first:
		return []
	count = int(round((last - first) / step)) + 1
	return [round(first + index * step, 6) for index in range(count)]


def select_era5_points(geometry: Any, minimum_points: int = 3, maximum_points: int = 3) -> tuple[list[tuple[float, float]], bool]:
	"""Select regular ERA5 grid points inside a district, with flagged fallback."""
	min_lon, min_lat, max_lon, max_lat = geometry.bounds
	centroid = geometry.centroid
	inside = [
		(lat, lon)
		for lat in _regular_grid_values(min_lat, max_lat)
		for lon in _regular_grid_values(min_lon, max_lon)
		if geometry.covers(Point(lon, lat))
	]
	if len(inside) >= minimum_points:
		selected = [min(inside, key=lambda point: (point[1] - centroid.x) ** 2 + (point[0] - centroid.y) ** 2)]
		while len(selected) < min(maximum_points, len(inside)):
			selected.append(
				max(
					(point for point in inside if point not in selected),
					key=lambda point: (
						min((point[1] - chosen[0]) ** 2 + (point[0] - chosen[1]) ** 2 for chosen in selected),
						-point[0],
						-point[1],
					),
				)
			)
		return selected, False

	centroid_point = (float(centroid.y), float(centroid.x))
	search = [
		(lat, lon)
		for lat in _regular_grid_values(centroid.y - 1.0, centroid.y + 1.0)
		for lon in _regular_grid_values(centroid.x - 1.0, centroid.x + 1.0)
	]
	points = [centroid_point]
	used_cells = {
		(round(round(centroid_point[0] / ERA5_GRID_RESOLUTION) * ERA5_GRID_RESOLUTION, 6),
		 round(round(centroid_point[1] / ERA5_GRID_RESOLUTION) * ERA5_GRID_RESOLUTION, 6))
	}
	for point in sorted(
		search,
		key=lambda item: ((item[1] - centroid.x) ** 2 + (item[0] - centroid.y) ** 2, item[0], item[1]),
	):
		cell = (
			round(round(point[0] / ERA5_GRID_RESOLUTION) * ERA5_GRID_RESOLUTION, 6),
			round(round(point[1] / ERA5_GRID_RESOLUTION) * ERA5_GRID_RESOLUTION, 6),
		)
		if cell in used_cells or any(
			math.hypot(cell[0] - used[0], cell[1] - used[1]) <= ERA5_GRID_RESOLUTION * 1.5
			for used in used_cells
		):
			continue
		points.append(point)
		used_cells.add(cell)
		if len(points) == minimum_points:
			break
	if len(points) < minimum_points:
		raise ValueError(f"Could not find {minimum_points} distinct ERA5 grid points near polygon centroid.")
	return points[:maximum_points], True


def _era5_year_chunks(start_date: date, end_date: date) -> list[tuple[date, date]]:
	chunks: list[tuple[date, date]] = []
	for year in range(start_date.year, end_date.year + 1):
		chunk_start = max(start_date, date(year, 1, 1))
		chunk_end = min(end_date, date(year, 12, 31))
		if chunk_start <= chunk_end:
			chunks.append((chunk_start, chunk_end))
	return chunks


def _era5_url(points: list[tuple[float, float]], start_date: date, end_date: date) -> str:
	from urllib.parse import urlencode

	params = {
		"latitude": ",".join(f"{lat:.6f}" for lat, _ in points),
		"longitude": ",".join(f"{lon:.6f}" for _, lon in points),
		"start_date": start_date.isoformat(),
		"end_date": end_date.isoformat(),
		"daily": "precipitation_sum",
		"models": ERA5_MODEL,
		"timezone": "UTC",
	}
	return f"{OPEN_METEO_ARCHIVE_URL}?{urlencode(params)}"


def verify_era5_response(
	response_data: Any,
	points: list[tuple[float, float]],
	start_date: date,
	end_date: date,
) -> list[dict[str, Any]]:
	"""Validate all point series exactly match requested dates and valid values."""
	locations = response_data if isinstance(response_data, list) else [response_data]
	if len(locations) != len(points):
		raise ValueError(f"ERA5 returned {len(locations)} locations; requested {len(points)}.")
	expected_dates = pd.date_range(start_date, end_date, freq="D").strftime("%Y-%m-%d").tolist()
	effective_cells: set[tuple[float, float]] = set()
	for location in locations:
		if location.get("daily_units", {}).get("precipitation_sum") != "mm":
			raise ValueError("Open-Meteo did not return precipitation_sum in mm.")
		daily = location.get("daily", {})
		dates = daily.get("time", [])
		values = daily.get("precipitation_sum", [])
		if len(dates) != len(set(dates)):
			raise ValueError("ERA5 response contains duplicate dates.")
		if dates != expected_dates:
			raise ValueError(
				f"ERA5 dates do not exactly match {start_date}..{end_date}: "
				f"received {len(dates)} records from {dates[0] if dates else None} "
				f"through {dates[-1] if dates else None}."
			)
		if len(values) != len(expected_dates):
			raise ValueError("ERA5 precipitation length differs from requested date count.")
		try:
			numeric = np.asarray(values, dtype=np.float64)
		except (TypeError, ValueError) as exc:
			raise ValueError("ERA5 precipitation contains non-numeric or missing values.") from exc
		if not np.isfinite(numeric).all():
			raise ValueError("ERA5 precipitation contains missing or non-finite values.")
		if (numeric < 0).any():
			raise ValueError("ERA5 precipitation contains negative values.")
		if "latitude" not in location or "longitude" not in location:
			raise ValueError("ERA5 response omitted its effective grid coordinates.")
		effective_cells.add((round(float(location["latitude"]), 5), round(float(location["longitude"]), 5)))
	if len(effective_cells) < 3:
		raise ValueError(
			f"ERA5 points resolve to only {len(effective_cells)} unique grid cells; at least 3 are required."
		)
	return locations


def verify_open_meteo_api(session: requests.Session | None = None) -> dict[str, Any]:
	"""Verify the public ERA5 daily endpoint before a data retrieval run."""
	client = session or requests.Session()
	points = [(19.0, 73.0), (21.0, 79.0), (18.5, 73.75)]
	start_date, end_date = date(2000, 5, 2), date(2000, 5, 3)
	data, attempts, url = _request_era5_chunk(points, start_date, end_date, client)
	verify_era5_response(data, points, start_date, end_date)
	return {
		"url": OPEN_METEO_ARCHIVE_URL,
		"model": ERA5_MODEL,
		"verified_points": len(points),
		"request_attempts": attempts,
	}


def _request_era5_chunk(
	points: list[tuple[float, float]],
	start_date: date,
	end_date: date,
	session: requests.Session,
) -> tuple[Any, int, str]:
	url = _era5_url(points, start_date, end_date)
	for attempt in range(1, ERA5_RETRIES + 1):
		try:
			response = session.get(url, timeout=(45, 180))
			if response.status_code == 429 or response.status_code >= 500:
				raise requests.HTTPError(response=response)
			response.raise_for_status()
			data = response.json()
			time.sleep(ERA5_REQUEST_SPACING_SECONDS)
			return data, attempt, url
		except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
			status = getattr(getattr(exc, "response", None), "status_code", None)
			if attempt >= ERA5_RETRIES or (status is not None and status != 429 and status < 500):
				raise
			retry_response = getattr(exc, "response", None)
			retry_after = getattr(retry_response, "headers", {}).get("Retry-After")
			try:
				default_delay = min(5 * 2 ** (attempt - 1), 60) if status == 429 else min(2 ** (attempt - 1), 30)
				delay = float(retry_after) if retry_after is not None else default_delay
			except ValueError:
				delay = default_delay
			logger.warning(
				"Open-Meteo request failed (HTTP %s: %s); retry %d/%d in %.1fs",
				status if status is not None else "network",
				str(exc) or "no error detail",
				attempt,
				ERA5_RETRIES,
				delay,
			)
			time.sleep(min(delay, 60.0))
	raise RuntimeError("Unreachable ERA5 retry loop.")


def fetch_era5_district(
	code: int,
	geometry: Any,
	start_date: date = DEFAULT_START_DATE,
	end_date: date = DEFAULT_END_DATE,
	cache_dir: str | Path = ERA5_CACHE_DIR,
	force: bool = False,
	session: requests.Session | None = None,
) -> tuple[pd.Series, dict[str, Any]]:
	"""Fetch/cache yearly ERA5 chunks and return the daily average across points."""
	points, approximate = select_era5_points(geometry)
	cache = Path(cache_dir)
	cache.mkdir(parents=True, exist_ok=True)
	client = session or requests.Session()
	series_parts: list[pd.Series] = []
	request_attempts = 0
	cached_request_attempts = 0
	cache_hits = 0
	for chunk_start, chunk_end in _era5_year_chunks(start_date, end_date):
		path = cache / f"era5_lgd_{int(code)}_{chunk_start.year}.json"
		if path.exists() and not force:
			cached = json.loads(path.read_text(encoding="utf-8"))
			metadata = cached["_climatesense"]
			cached_points = tuple((float(point[0]), float(point[1])) for point in metadata["points"])
			if (
				metadata["model"] != ERA5_MODEL
				or cached_points != tuple(points)
				or metadata["start_date"] != chunk_start.isoformat()
				or metadata["end_date"] != chunk_end.isoformat()
			):
				raise ValueError(f"ERA5 cache metadata does not match this request: {path}")
			data = cached["response"]
			cached_request_attempts += int(metadata.get("request_attempts", 0))
			cache_hits += 1
		else:
			data, attempts, url = _request_era5_chunk(points, chunk_start, chunk_end, client)
			request_attempts += attempts
			validated = verify_era5_response(data, points, chunk_start, chunk_end)
			payload = {
				"_climatesense": {
					"model": ERA5_MODEL,
					"points": points,
					"approximate_centroid_fallback": approximate,
					"start_date": chunk_start.isoformat(),
					"end_date": chunk_end.isoformat(),
					"request_attempts": attempts,
					"url": url,
				},
				"response": validated,
			}
			temporary = path.with_suffix(path.suffix + ".part")
			temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
			temporary.replace(path)
			data = validated
		locations = verify_era5_response(data, points, chunk_start, chunk_end)
		precipitation = np.asarray(
			[location["daily"]["precipitation_sum"] for location in locations], dtype=np.float64
		)
		means = precipitation.mean(axis=0)
		dates = pd.DatetimeIndex(pd.to_datetime(locations[0]["daily"]["time"]))
		series_parts.append(pd.Series(means, index=dates, name="rainfall_mm"))
	series = pd.concat(series_parts).sort_index()
	if series.index.has_duplicates:
		raise ValueError(f"ERA5 district series for LGD {code} has duplicate dates.")
	expected = pd.date_range(start_date, end_date, freq="D")
	if not series.index.equals(expected):
		missing = expected.difference(series.index)
		extra = series.index.difference(expected)
		raise ValueError(f"ERA5 district {code} coverage mismatch; missing={len(missing)}, extra={len(extra)}.")
	if not np.isfinite(series.to_numpy()).all() or (series.to_numpy() < 0).any():
		raise ValueError(f"ERA5 district {code} average rainfall is missing or negative.")
	return series, {
		"lgd_code": int(code),
		"points": points,
		"point_count": len(points),
		"approximate_centroid_fallback": approximate,
		"request_attempts_this_run": request_attempts,
		"cached_archive_request_attempts": cached_request_attempts,
		"cache_chunks_used": len(_era5_year_chunks(start_date, end_date)),
		"cache_hits": cache_hits,
		"date_count": len(series),
		"start_date": start_date.isoformat(),
		"end_date": end_date.isoformat(),
		"model": ERA5_MODEL,
	}


def fetch_era5_districts(
	codes: Iterable[int] = DISTRICT_NAMES,
	start_date: date = DEFAULT_START_DATE,
	end_date: date = DEFAULT_END_DATE,
	boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
	cache_dir: str | Path = ERA5_CACHE_DIR,
	force: bool = False,
) -> tuple[dict[int, pd.Series], dict[str, Any]]:
	"""Verify the API, fetch bounded annual chunks, and enforce daily completeness."""
	api = verify_open_meteo_api()
	boundaries = load_selected_boundaries(boundary_path, codes)
	series: dict[int, pd.Series] = {}
	metadata: dict[str, Any] = {
		"api_check": api,
		"districts": {},
		"request_attempts": int(api["request_attempts"]),
	}
	for code, (name, geometry) in boundaries.items():
		daily, district_metadata = fetch_era5_district(
			code,
			geometry,
			start_date,
			end_date,
			cache_dir=cache_dir,
			force=force,
		)
		district_metadata["district"] = name
		series[code] = daily
		metadata["districts"][str(code)] = district_metadata
		metadata["request_attempts"] += district_metadata["request_attempts_this_run"]
		metadata.setdefault("cached_archive_request_attempts", 0)
		metadata["cached_archive_request_attempts"] += district_metadata["cached_archive_request_attempts"]
	return series, metadata


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--codes", default=",".join(map(str, DISTRICT_NAMES)))
	parser.add_argument("--start-date", default=DEFAULT_START_DATE.isoformat())
	parser.add_argument("--end-date", default=DEFAULT_END_DATE.isoformat())
	parser.add_argument("--boundary", default=str(DEFAULT_BOUNDARY_PATH))
	parser.add_argument("--cache-dir", default=str(ERA5_CACHE_DIR))
	parser.add_argument("--force", action="store_true")
	args = parser.parse_args()
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	codes = [int(value) for value in args.codes.split(",") if value.strip()]
	try:
		rainfall, metadata = fetch_era5_districts(
			codes,
			date.fromisoformat(args.start_date),
			date.fromisoformat(args.end_date),
			boundary_path=args.boundary,
			cache_dir=args.cache_dir,
			force=args.force,
		)
	except (FileNotFoundError, requests.RequestException, ValueError) as exc:
		logger.error("%s", exc)
		raise SystemExit(2) from exc
	daily_frames = [
		pd.DataFrame(
			{
				"date": daily.index.strftime("%Y-%m-%d"),
				"lgd_code": code,
				"district": metadata["districts"][str(code)]["district"],
				"precipitation_sum_mm": daily.to_numpy(),
			}
		)
		for code, daily in rainfall.items()
	]
	rainfall_path = Path(args.cache_dir) / "district_daily_rainfall.csv"
	pd.concat(daily_frames, ignore_index=True).to_csv(rainfall_path, index=False)
	metadata.update(
		{
			"source": OPEN_METEO_ARCHIVE_URL,
			"model": ERA5_MODEL,
			"variable": "daily.precipitation_sum",
			"units": "mm/day",
			"license": "CC BY 4.0",
			"reanalysis_not_observed_rainfall": True,
			"retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
			"daily_dates_per_district": len(pd.date_range(args.start_date, args.end_date, freq="D")),
			"daily_rainfall_csv": str(rainfall_path),
		}
	)
	manifest_path = Path(args.cache_dir) / "fetch_manifest.json"
	manifest_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
	print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
	main()