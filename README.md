# Project Deep Bet

**Team Veritas | Hawaii Annual Innovation Challenge 2026**

Project Deep Bet is an interactive research prototype for
exploring community conditions across Hawaii's 51 State
House districts using Census data and geographic analysis.

## Features

- Interactive legislative district and census tract map
- District search, ranges, and demographic filters
- District Intelligence Reports and needs prioritization
- Potential assistance-program matching
- CSV inspection and geographic validation
- Rule-based data quality and source screening
- Experimental Census API retrieval interface

## Data

- 2024 American Community Survey 5-year estimates
- 2025 U.S. Census TIGER/Line boundaries
- Census tract to House district geographic crosswalk

See DATA_SOURCES.md for additional information.

## Installation

Create a Python virtual environment, activate it, then run:

    pip install -r requirements.txt
    streamlit run app.py

## Methodology and Limitations

District indicators use unweighted medians across overlapping
census tracts, not population-weighted district estimates.
A census tract may overlap multiple House districts.

Community needs classifications are prototype comparisons,
not official government standards.

Assistance-program matches indicate potential relevance,
not individual eligibility.

External screening is deterministic and rule-based.
It is not a trained artificial intelligence model.
Declared external sources are not independently authenticated.

Live Census API retrieval may be unavailable without an
API key. Existing district analysis works independently.

This is a research prototype, not an official government system.

## Project Modules

- app.py: Streamlit dashboard
- district_intelligence.py: District intelligence
- external_data.py: CSV inspection
- geographic_validation.py: Geographic validation
- data_screening.py: Rule-based quality screening
- external_retrieval.py: Approved API retrieval
- build_crosswalk.py: Geographic crosswalk generation

## Team

Veritas - Hawaii Annual Innovation Challenge 2026
