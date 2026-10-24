# Income layer: source and geographic matching

## Published estimates

- Original producer: U.S. Census Bureau, American Community Survey (ACS).
- Publisher of the NTA compilation: NYC Department of City Planning, Population Division.
- Official source: [2014–2018 ACS Economic Profile by NTA](https://www.nyc.gov/assets/planning/download/office/planning-level/nyc-population/acs/econ_2018_acs5yr_nta.xlsx).
- Source worksheet: `EconData`. Definitions are in `Dictionary`; the workbook's `About` sheet identifies the ACS period and Population FactFinder processing.
- Measure: median household income, field `MdHHIncE`; 90% margin of error, `MdHHIncM`. These are survey estimates of annual household income, not individual earnings.
- Reference period: 2014–2018 ACS five-year estimates. Dollar basis: 2018 inflation-adjusted dollars. The estimates do not describe current incomes.
- Geography: `GeoType = NTA2010`. Join key: source `GeoID` to map `ntacode` (for example, `MN34`).
- Retrieved: October 23, 2026. The source SHA-256 is recorded on every exported income record.

## Why this vintage

The existing map uses NTA2010 polygons. The official 2015–2019 economic workbook currently published at `econ_2019_acs5yr_nta.xlsx` contains `NTA2020` geography with different codes and boundaries. It cannot be directly substituted into this map. The selected 2014–2018 file explicitly supplies NTA2010 estimates. This choice establishes a boundary-compatible baseline, not a claim that these are the newest income estimates available.

## Join and missing-data rules

The income join uses exact codes only, with no neighborhood-name matching, spatial redistribution, borough averages, or averaging of tract medians. The income source has 195 distinct NTA2010 codes and 191 numeric median-income estimates. Four source records have no income estimate: BX98 (Rikers Island), MN99 (park-cemetery-etc-Manhattan), QN98 (Airport), and SI99 (park-cemetery-etc-Staten Island). Missing estimates remain null and display as no data. Other geography exclusions follow the existing map filter. With the primary geography service used for validation, all 188 displayed neighborhoods have exact code matches and published income estimates.

The dashboard embeds the published income records so a separate income service failure cannot activate the previous generated values. The accompanying CSV preserves source names, raw estimate values, margins of error, period, geography, field names, retrieval date and source URL. The dashboard's dataset download includes these fields for each displayed map record. Source names may differ in punctuation from polygon display names; only codes determine matches.

## Interpretation and affected outputs

The former starter incomes, borough income presets and neighborhood income multipliers have been removed from the active data paths. No generated income fallback is used. Income metadata is separate from asthma data status. Margins of error appear in neighborhood cards; rankings remain descriptive and do not test whether differences are statistically significant.

Poverty, education and race/ethnicity still use the pre-existing unverified starter/generated data and are visibly identified as provisional. The working-class score and classification are disabled because they would combine the corrected income measure with unverified poverty and education inputs. These other demographic measures require a separate source audit before substantive use.

Asthma retains its existing EHDP loading and fallback behavior. Its latest source periods may differ from the income period; a common-period analysis has not been performed. Neither geographic matching nor side-by-side viewing demonstrates an association or causal relationship. No income–asthma interpretation is presented as a finding.

## Reproduction

Download the official workbook above as `econ2018.xlsx`. The committed `replace_income.py` documents the source extraction and replacement procedure used for this correction. It extracts the published NTA estimates directly from the workbook's XML; it does not calculate medians. Run it against the pre-correction `index.html` when reproducing the migration. It is a one-time migration script, not a recurring refresh job.
