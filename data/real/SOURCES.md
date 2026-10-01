# Real Data Sources

## IFI-Impacts

- Dataset: India Flood Inventory-Impacts (IFI-Impacts) [1967-2023]
- Concept DOI: https://doi.org/10.5281/zenodo.4742142
- Latest record resolved on 2026-09-30: https://zenodo.org/records/16994648 (record ID 16994648; parent/concept record 4742142)
- API metadata: https://zenodo.org/api/records/4742142
- License: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0), https://creativecommons.org/licenses/by-nc/4.0/
- Access method: Zenodo REST API; original CSV assets downloaded from the latest record's `files/{filename}/content` endpoints. Zenodo returned record MD5 checksums; local SHA-256 values below were also calculated. The downloaded `ifi/zenodo_record.json` preserves the record metadata and dataset description. The record lists no separate README or codebook file.
- Dataset citation: Saharia, M. (2025). *India Flood Inventory-Impacts (IFI-Impacts) [1967-2023]: A multi-source national geospatial database to facilitate comprehensive flood research* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.16994648. Cite the concept DOI above when referring to the version-independent record.

Related references cited by the Zenodo record:

- Saharia, M., Jain, A., Baishya, R.R., Haobam, S., Sreejith, O.P., Pai, D.S., & Rafieeinasab, A. (2021). India flood inventory: creation of a multi-source national geospatial database to facilitate comprehensive flood research. *Natural Hazards*. https://doi.org/10.1007/s11069-021-04698-6
- Saharia, M., Jain, S.K., Prakash, V., Malik, H., Sreejith, O.P., & Joshi, D. (2025). A district-level flood severity index for flood management in India. *Natural Hazards*. https://doi.org/10.1007/s11069-025-07493-9

## Downloaded Files and Checksums

Checksums are SHA-256 (local) and MD5 (as declared by Zenodo and verified against each downloaded CSV).

| Local file | Zenodo file URL | Bytes | SHA-256 | Zenodo MD5 |
|---|---|---:|---|---|
| `ifi/India_Flood_Inventory_v3.csv` | https://zenodo.org/api/records/16994648/files/India_Flood_Inventory_v3.csv/content | 1801579 | `ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108` | `fea75a9ff9eba8fb328eaddfacd21d67` |
| `ifi/District_FloodImpact.csv` | https://zenodo.org/api/records/16994648/files/District_FloodImpact.csv/content | 19122 | `0cc7381e8153cdd34e287540e64947e4cd2e5ff46d2461581e7b6c041b3655fb` | `231d4157f462ea6c9bfd728c9dfbf520` |
| `ifi/District_FloodedArea.csv` | https://zenodo.org/api/records/16994648/files/District_FloodedArea.csv/content | 32567 | `738d5edf8a29c70de520b3b7b8e148eb7eed2ce89bbd9f0ecacd3cbc17b07610` | `52744304c21f28b841fb3a28e510e789` |
| `ifi/DFSI.csv` | https://zenodo.org/api/records/16994648/files/DFSI.csv/content | 29118 | `25cb6ad0ad7b8b681ece2c99dcc6030de1debf2569f5e8e8a47a4144d90a8cac` | `d15cbab2f15c3a6c393fd45220665211` |
| `ifi/zenodo_record.json` | https://zenodo.org/api/records/16994648/versions/latest | 6163 | `b684777228f5543e036a253301c657ebb76d4b16ee20b374acdd49595c16462a` | Not supplied for this locally retained metadata response |

The latest record metadata does not set a machine-readable `version` value. It describes the v3 inventory with LGD codes and v4.0's District Flood Severity Index; the resolved record ID, title, publication date, license, and file list are retained in `ifi/zenodo_record.json`.

## District Boundaries

- Dataset: LGD district administrative boundaries, 785 district features.
- Upstream source: Local Government Directory (LGD), Ministry of Panchayati Raj, Government of India.
- Access/distribution: [india-geodata `admin/districts` release](https://github.com/yashveeeeeeer/india-geodata/releases/tag/admin/districts), asset `LGD_Districts.parquet`, released 2026-03-08. The repository documents the release source as LGD and its release files as CC0/public domain; this is a third-party redistribution of government boundary data.
- Upstream repository: https://github.com/yashveeeeeeer/india-geodata
- Local file: `boundaries/LGD_Districts.parquet`
- License for release asset: CC0, https://creativecommons.org/publicdomain/zero/1.0/
- SHA-256 (release and locally verified): `c205da56ce0538b33b2f66838a4032cef79be7585543686892c8a85a5d21aebc`
- Identifier fields: `dist_lgd` is the LGD district code; `state_lgd` is the LGD state code. The layer also contains `dtcode11` and `stcode11` Census-2011 codes. Selected IFI LGD codes 482, 484, 490, 497, and 499 each matched exactly one valid Maharashtra polygon; no name-based join or centroid fallback was used.

## CHIRPS Availability Check

- Dataset ID: `chirps20GlobalDailyP05`; info URL: https://coastwatch.pfeg.noaa.gov/erddap/info/chirps20GlobalDailyP05/index.json
- The info endpoint returned HTTP 200, identified daily `precip` in mm/day and nominal 0.05-degree resolution. The requested bounding-box NetCDF probe succeeded for one Mumbai grid window on 2000-05-02.
- The requested complete coverage was not available from the live time-coordinate response. A query for 2000-01-01 through 2023-12-31 returned daily coordinates only in years 2000, 2004, 2008, 2012, 2016, and 2020, plus a stray 2024-01-01 coordinate. Requests for missing-year dates returned a neighboring date rather than the requested date. The fetcher therefore rejects incomplete time axes before district downloads. No full-period district rainfall cache or labeled dataset has been created.

## ERA5 Rainfall via Open-Meteo Historical Weather API

- API: https://archive-api.open-meteo.com/v1/archive
- Dataset/model parameter: `models=era5`; daily variable `precipitation_sum`; timezone UTC; units mm/day.
- Verification: successful HTTP 200 responses for two-day 2000-05-02/03 requests with `models=era5`, including a multi-point response. The alternative `models=era5_land` returned null precipitation for the same sample dates, so it is not used.
- Access: public API, no API key; yearly chunks and multiple point coordinates are requested separately for each selected district. Only district-selected grid points/nearest fallback points are queried; no global grid file is downloaded.
- License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/.
- Retrieval date: 2026-10-01.
- Spatial sampling: three distinct effective ERA5 cells per district. The three selected query points are inside each LGD polygon where possible. Mumbai has fewer than three grid points inside its small polygon, so it uses the polygon centroid plus nearest distinct cells outside the polygon; this is flagged `approximate_centroid_fallback=true` in cached metadata. The other selected districts use three cells inside their polygons.
- Caveat: ERA5 is atmospheric reanalysis, not observed station rainfall. Open-Meteo returns effective model grid-cell coordinates; each district's daily `precipitation_sum` is the arithmetic mean across its three selected effective cells.
- Required date coverage: 2000-05-02 through 2023-09-29 inclusive. Each cached point response is checked against every expected UTC date; missing, duplicate, non-finite, negative, or mismatched records fail rather than being filled.
- Cache location: `data/real/era5/three_point/`; per-district/year JSON responses, `district_daily_rainfall.csv` (long format, 42,755 district-date means), and `fetch_manifest.json`. The earlier five-point cache under `data/real/era5/archive/` is retained unchanged and is not used for this result.
- Completeness: 8,551 dates per district, 42,755 district-date means total. The completed run recorded 124 HTTP request attempts: 120 yearly data chunks, two retries, and two API-verification attempts. The manifest records the per-district attempt counts and full date coverage.