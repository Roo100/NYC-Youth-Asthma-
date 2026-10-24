# Current income layer and automatic refresh

Income now uses NYC Planning's latest published ACS five-year economic profile by NTA. The initial release is **2020–2024 ACS**, in **2024 inflation-adjusted dollars**, for **197 residential NTA2020 neighborhoods**. It replaces the earlier 2014–2018 layer.

## Official sources

- [NYC Planning ACS release catalog](https://www.nyc.gov/content/planning/pages/resources/datasets/american-community-survey).
- [Machine-readable release catalog](https://apps.nyc.gov/content-api/v1/content/planning/resources/datasets/american-community-survey).
- [Current economic workbook](https://s-media.nyc.gov/agencies/dcp/assets/files/excel/data-tools/population/american-community-survey/Econ_2024ACS5YR_NTA.xlsx).
- [Official NTA2020 boundaries](https://data.cityofnewyork.us/City-Government/2020-Neighborhood-Tabulation-Areas-NTAs/9nt8-h7nd).

The U.S. Census Bureau produces the ACS. NYC Department of City Planning compiles the NTA estimates for Population FactFinder. The workbook's About sheet explicitly identifies the 2020–2024 reference period. EconData supplies median household income (MdHHIncE) and its 90% margin of error (MdHHIncM). The Data Dictionary identifies the measure's universe as households. These are estimates of annual household income, not individual earnings or current-year income.

## Automatic updates and reliability

The GitHub Actions workflow Refresh official neighborhood income runs daily at 10:17 UTC and can also run manually. scripts/refresh_income.py discovers the highest release year linked as an NTA economic workbook in the official catalog. It downloads the workbook and official geometry, validates them, and saves data/income_latest.json and data/income_latest.csv. It commits the validated snapshot and requests a GitHub Pages rebuild. A newer annual release will be adopted without changing a year in the dashboard code, provided the supported workbook schema and NTA2020 geography remain compatible.

Validation requires the workbook's period to match the release, expected columns, unique NTA2020 codes, sufficient estimate coverage, and exact equality of residential income and boundary codes. A source error, schema change, incomplete release, or geography change fails the job instead of overwriting the last validated snapshot. Requests have timeouts and retries. A newer stored release cannot be overwritten with an older release.

The dashboard fetches the same-origin snapshot without a browser cache on every page load. It displays the reference period, dollar year and last successful source-check timestamp. After three days without a source check, it visibly identifies the refresh as overdue. The last validated snapshot remains available if the official income source is temporarily down. A malformed or missing dashboard snapshot displays an error rather than substituting generated or historical income values. Annual ACS publication is distinct from the daily update check; daily checks do not create daily income observations.

Source URL, source-workbook SHA-256, reference period, dollar year and check timestamp are preserved in the downloadable data. Estimates and margins of error retain published precision in the data; the map rounds dollar displays to whole dollars. Nulls remain unavailable.

## Matching boundaries

Income uses exact GeoID to nta2020 matches, with NTAType = 0 / ntatype = 0 selecting residential neighborhoods. No name matching, borough presets, interpolated income values or averages of tract medians are used. The browser validates income codes against official geometry before activating the income map. A boundary-service failure leaves the previous map selected and provides a retry message.

Asthma indicators remain NTA2010. Selecting income switches the map to NTA2020 and its corresponding rankings, neighborhood details and CSV export. Switching back restores the original asthma geography and data. NTA2010 asthma values are not attached to NTA2020 polygons, so income cards do not show asthma values. Harmonizing both strands for a statistical comparison remains separate work.

Pre-existing poverty, education and race/ethnicity layers remain provisional, and the working-class score remains disabled. No income–asthma association or causal finding is asserted.

## Reproduce and inspect

Run python scripts/refresh_income.py with Python 3.12 and network access. No third-party packages or API key are required. Inspect workflow history for failures and the snapshot's checked_at, release_year, reference_period, geography and source_sha256 for provenance. The older income CSV and one-time migration script are historical artifacts and are not used by the dashboard or refresh process.
