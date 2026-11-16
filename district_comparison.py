"""Compare official ACS district and statewide estimates."""

import csv
from pathlib import Path

from demographic_engine import calculate_demographics


DISTRICT_FILE = Path(
    "data/demographics/hawaii_legislative_districts_acs2024.csv"
)
STATE_FILE = Path(
    "data/demographics/hawaii_statewide_acs2024.csv"
)

METRIC_LABELS = {
    "population": "Population",
    "children_under_18_pct": "Under 18 (%)",
    "kupuna_65_plus_pct": "Age 65+ (%)",
    "median_household_income": "Median Household Income ($)",
    "poverty_rate_pct": "Poverty Rate (%)",
    "unemployment_rate_pct": "Civilian Unemployment Rate (%)",
    "industry_employed_total": "Civilian Employed Residents",
}

PERCENT_METRICS = {
    "children_under_18_pct",
    "kupuna_65_plus_pct",
    "poverty_rate_pct",
    "unemployment_rate_pct",
}


def read_dataset(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_record(record):
    translated = {}

    for field, value in record.items():
        if "_E" not in field:
            continue

        table, number = field.split("_E", 1)

        if table in ("B01001", "B17001", "B23025", "C24030"):
            translated[f"{table}_{number}E"] = value

    result = calculate_demographics(translated)

    raw_income = record.get("B19013_E001")
    try:
        income = int(raw_income)
        if income < 0:
            income = None
    except (TypeError, ValueError):
        income = None

    result["median_household_income"] = income
    return result


def load_comparison_data(
    district_path=DISTRICT_FILE,
    statewide_path=STATE_FILE,
):
    district_rows = read_dataset(district_path)
    state_rows = read_dataset(statewide_path)

    if len(state_rows) != 1:
        raise ValueError("Expected exactly one statewide ACS record")

    if state_rows[0].get("GEO_ID") != "0400000US15":
        raise ValueError("Unexpected statewide geography")

    districts = {}

    for row in district_rows:
        chamber = row.get("chamber")
        district = row.get("district")

        if chamber not in ("House", "Senate"):
            raise ValueError("Invalid legislative chamber")

        if district is None or not district.isdigit():
            raise ValueError("Invalid district identifier")

        key = (chamber, district.zfill(3))

        if key in districts:
            raise ValueError("Duplicate legislative district")

        districts[key] = normalize_record(row)

    expected = (
        {("House", f"{i:03d}") for i in range(1, 52)}
        | {("Senate", f"{i:03d}") for i in range(1, 26)}
    )

    if set(districts) != expected:
        raise ValueError("Incomplete legislative district coverage")

    statewide = normalize_record(state_rows[0])
    return districts, statewide


def compare_districts(chamber_a, district_a, chamber_b, district_b):
    districts, statewide = load_comparison_data()

    key_a = (chamber_a, str(district_a).zfill(3))
    key_b = (chamber_b, str(district_b).zfill(3))

    if key_a not in districts:
        raise ValueError(f"Unknown first district: {key_a}")

    if key_b not in districts:
        raise ValueError(f"Unknown second district: {key_b}")

    a = districts[key_a]
    b = districts[key_b]

    comparison = []

    for metric, label in METRIC_LABELS.items():
        value_a = a.get(metric)
        value_b = b.get(metric)
        state_value = statewide.get(metric)

        difference = (
            value_a - value_b
            if value_a is not None and value_b is not None
            else None
        )

        difference_from_state_a = (
            value_a - state_value
            if value_a is not None and state_value is not None
            else None
        )

        difference_from_state_b = (
            value_b - state_value
            if value_b is not None and state_value is not None
            else None
        )

        comparison.append({
            "metric": metric,
            "label": label,
            "district_a": value_a,
            "district_b": value_b,
            "statewide": state_value,
            "a_minus_b": difference,
            "a_minus_state": difference_from_state_a,
            "b_minus_state": difference_from_state_b,
            "difference_unit": (
                "percentage points"
                if metric in PERCENT_METRICS
                else "units"
            ),
        })

    return {
        "district_a": key_a,
        "district_b": key_b,
        "metrics": comparison,
        "industries_a": a["industries"],
        "industries_b": b["industries"],
        "industries_statewide": statewide["industries"],
        "source": "U.S. Census Bureau, 2024 ACS 5-year estimates",
        "limitations": (
            "District and statewide estimates are direct ACS geographic "
            "estimates. Differences are descriptive and have not been "
            "tested for statistical significance. Margins of error for "
            "derived percentages and differences are not calculated. "
            "Statewide totals are not district averages."
        ),
    }
