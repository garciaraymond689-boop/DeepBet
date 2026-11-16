# Project Deep Bet

**Team Veritas | Hawaii Annual Innovation Challenge 2026**

Project Deep Bet is an interactive research prototype for
exploring community conditions across Hawaii's 51 State House and 25 State Senate districts using Census data and geographic analysis.

## Features

- Interactive House/Senate legislative district and census tract maps
- District search, ranges, and demographic filters
- District Intelligence Reports and needs prioritization
- Official 2024 ACS district-level demographic estimates
- District comparisons and statewide benchmarks
- Downloadable district PDF reports
- Local conversational AI with Ollama and Qwen2.5 3B
- Rule-based question assistant fallback
- Potential assistance-program matching
- CSV inspection and geographic validation
- Rule-based data quality and source screening
- Experimental Census API retrieval interface

## Data

- 2024 American Community Survey 5-year estimates
- 2025 U.S. Census TIGER/Line boundaries
- Census tract to House and Senate district geographic crosswalks
- Official legislative district ACS demographic tables

See DATA_SOURCES.md for additional information.

## Installation

Create a Python virtual environment, activate it, then run:

    pip install -r requirements.txt
    streamlit run app.py

## Methodology and Limitations

Selected tract-based district indicators use unweighted medians across overlapping
census tracts, not population-weighted district estimates.
A census tract may overlap multiple House districts.

Community needs classifications are prototype comparisons,
not official government standards.

Assistance-program matches indicate potential relevance,
not individual eligibility.

External source screening remains deterministic and rule-based.
The separate conversational assistant uses a local pretrained
Qwen2.5 3B language model with basic response validation.
AI responses require verification against underlying data.
Declared external sources are not independently authenticated.

Live Census API retrieval may be unavailable without an
API key. Existing district analysis works independently.

This is a research prototype, not an official government system.

## Local AI Setup

Install Ollama from https://ollama.com/ and run:

    ollama pull qwen2.5:3b

Ensure Ollama is running before using the local AI assistant.
The application does not require a paid OpenAI API key.

## Demonstration

1. Select House District 001.
2. Review the map and District Intelligence Report.
3. Download the district PDF.
4. Ask the local AI for the district population.
5. Switch to Senate District 001.
6. Compare district indicators and review their limitations.

## Project Modules

- app.py: Streamlit dashboard
- local_district_ai.py: Local conversational AI
- district_questions.py: Rule-based question assistant
- district_report.py: Downloadable PDF reports
- district_intelligence.py: District intelligence
- external_data.py: CSV inspection
- geographic_validation.py: Geographic validation
- data_screening.py: Rule-based quality screening
- external_retrieval.py: Approved API retrieval
- build_crosswalk.py: Geographic crosswalk generation

## Team

Veritas - Hawaii Annual Innovation Challenge 2026
