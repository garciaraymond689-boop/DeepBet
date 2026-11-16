# Deep Bet — Data Sources and Limitations

## Geographic boundaries

Source: U.S. Census Bureau, 2025 TIGER/Line Shapefiles
Geography: Hawaii (state FIPS 15)

- State House legislative districts: 51
- Census tracts: 461
- County coverage: All five Hawaii counties
- Coordinate reference system: EPSG:4269

Boundary files:
- data/boundaries/hawaii_house_districts.zip
- data/boundaries/hawaii_census_tracts.zip

## Demographic statistics

Source: U.S. Census Bureau
Dataset: 2024 American Community Survey (ACS), 5-year estimates
Geography: Census tract

Variables:
- B19013: Median household income
- B19001: Household income distribution
- B25070: Gross rent as a percentage of household income
- B25091: Owner costs as a percentage of household income
- B28002: Household internet subscriptions

Data files:
- data/demographics/hawaii_income_2024.csv
- data/demographics/hawaii_housing_2024.csv
- data/demographics/hawaii_homeowners_2024.csv
- data/demographics/hawaii_internet_2024.csv

## Geographic alignment

Census tracts and legislative districts do not always share boundaries.

The geographic crosswalk identifies 645 tract-to-House-district
intersections covering all 461 tracts and all 51 districts.

Crosswalk:
data/boundaries/tract_house_crosswalk.csv

The tract_fraction field represents the fraction of a tract's
geographic area overlapping a House district.

It does NOT represent the fraction of the tract's population
or households living in that district.

## Interpretation and limitations

- ACS figures are statistical estimates, not exact counts.
- Small-area estimates may have substantial margins of error.
- Some ACS values may be missing or suppressed.
- ACS 2024 five-year estimates describe the 2020-2024 period.
- Geographic boundaries are from 2025 TIGER/Line files.
- The application does not identify individual households or residents.
- Geographic overlap does not establish individual eligibility
  for government assistance.
- Area-weighted district estimates must be labeled as approximations.
- Income-bracket interpolation is an estimate, not a measured count.
- Renter and homeowner housing-cost burden must be calculated
  with their respective denominators.
- Data uploaded by users must retain source and methodology information.

## Intended use

Project Deep Bet is a nonpartisan, aggregate-data decision-support
prototype for understanding community conditions.

It is not intended for identifying individuals, making individual
benefit eligibility decisions, or presenting statistical estimates
as exact household-level facts.
