"""Demographic calculations from official ACS 2024 5-year estimates."""

import math


def census_value(record, field):
    """Return a valid nonnegative Census estimate, or None."""
    raw = record.get(field)

    if raw is None or isinstance(raw, bool):
        return None

    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(value) or value < 0:
        return None

    return value


def sum_fields(record, fields):
    values = [census_value(record, field) for field in fields]

    if any(value is None for value in values):
        return None

    return sum(values)


def percentage(numerator, denominator):
    if numerator is None or denominator is None:
        return None

    if denominator <= 0 or numerator > denominator:
        return None

    return 100.0 * numerator / denominator


CHILD_FIELDS = [
    *(f"B01001_{i:03d}E" for i in range(3, 7)),
    *(f"B01001_{i:03d}E" for i in range(27, 31)),
]

KUPUNA_FIELDS = [
    *(f"B01001_{i:03d}E" for i in range(20, 26)),
    *(f"B01001_{i:03d}E" for i in range(44, 50)),
]

# Non-overlapping top-level C24030 industry categories.
MALE_INDUSTRY_FIELDS = [
    3, 6, 7, 8, 9, 10, 13, 14, 17, 21, 24, 27, 28
]

FEMALE_INDUSTRY_FIELDS = [
    30, 33, 34, 35, 36, 37, 40, 41, 44, 48, 51, 54, 55
]

INDUSTRY_NAMES = [
    "Agriculture and mining",
    "Construction",
    "Manufacturing",
    "Wholesale trade",
    "Retail trade",
    "Transportation and utilities",
    "Information",
    "Finance and real estate",
    "Professional and administrative services",
    "Education, health and social assistance",
    "Arts, accommodation and food services",
    "Other services",
    "Public administration",
]


def calculate_demographics(record):
    population = census_value(record, "B01001_001E")
    children = sum_fields(record, CHILD_FIELDS)
    kupuna = sum_fields(record, KUPUNA_FIELDS)

    poverty_population = census_value(record, "B17001_001E")
    below_poverty = census_value(record, "B17001_002E")

    civilian_labor_force = census_value(record, "B23025_003E")
    unemployed = census_value(record, "B23025_005E")

    employed_by_industry = census_value(record, "C24030_001E")

    industries = {}

    for name, male, female in zip(
        INDUSTRY_NAMES,
        MALE_INDUSTRY_FIELDS,
        FEMALE_INDUSTRY_FIELDS,
    ):
        count = sum_fields(
            record,
            [f"C24030_{male:03d}E", f"C24030_{female:03d}E"],
        )

        industries[name] = {
            "count": count,
            "percent": percentage(count, employed_by_industry),
        }

    return {
        "population": population,
        "children_under_18": children,
        "children_under_18_pct": percentage(children, population),
        "kupuna_65_plus": kupuna,
        "kupuna_65_plus_pct": percentage(kupuna, population),
        "poverty_population": poverty_population,
        "below_poverty": below_poverty,
        "poverty_rate_pct": percentage(
            below_poverty, poverty_population
        ),
        "civilian_labor_force": civilian_labor_force,
        "unemployed": unemployed,
        "unemployment_rate_pct": percentage(
            unemployed, civilian_labor_force
        ),
        "industry_employed_total": employed_by_industry,
        "industries": industries,
        "source": "2024 ACS 5-year estimates",
    }
