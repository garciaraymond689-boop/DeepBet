import pandas as pd


def build_tract_indicators(income, housing, internet):
    """Create independent tract-level indicators."""

    indicators = pd.DataFrame(index=income.index.copy())
    indicators.index.name = "GEOID"

    indicators["median_income"] = pd.to_numeric(
        income["B19013_001E"], errors="coerce"
    )

    # ACS missing/suppressed values must not be treated as real incomes.
    indicators.loc[
        indicators["median_income"] < 0, "median_income"
    ] = float("nan")

    def numeric(frame, column):
        return pd.to_numeric(
            frame[column], errors="coerce"
        ).where(lambda values: values >= 0)

    renter_total = numeric(housing, "B25070_001E")
    renter_not_computed = numeric(housing, "B25070_011E")
    renter_burdened = sum(
        numeric(housing, f"B25070_{number:03d}E")
        for number in range(7, 11)
    )

    renter_denominator = renter_total - renter_not_computed

    indicators["renter_burden_pct"] = (
        100 * renter_burdened / renter_denominator.where(
            renter_denominator > 0
        )
    )

    internet_total = numeric(internet, "B28002_001E")
    without_internet = numeric(internet, "B28002_013E")

    indicators["no_internet_pct"] = (
        100 * without_internet / internet_total.where(
            internet_total > 0
        )
    )

    for column in ["renter_burden_pct", "no_internet_pct"]:
        indicators[column] = indicators[column].where(
            indicators[column].between(0, 100)
        )

    return indicators


def build_district_profiles(indicators, crosswalk, chamber="House"):
    """Summarize overlapping tracts for House or Senate districts."""
    if chamber not in ("House", "Senate"):
        raise ValueError("Chamber must be House or Senate.")
    district_column = chamber.lower() + "_district"

    links = crosswalk[
        ["tract_geoid", district_column]
    ].drop_duplicates().copy()

    links["tract_geoid"] = links["tract_geoid"].astype(str)
    links[district_column] = (
        links[district_column].astype(str).str.zfill(3)
    )

    tract_rows = indicators.reset_index().merge(
        links,
        left_on="GEOID",
        right_on="tract_geoid",
        how="inner"
    )

    profiles = (
        tract_rows.groupby(district_column)
        .agg(
            tract_count=("GEOID", "nunique"),
            median_income=("median_income", "median"),
            renter_burden_pct=("renter_burden_pct", "median"),
            no_internet_pct=("no_internet_pct", "median")
        )
        .reset_index()
    )

    return profiles, tract_rows


def statewide_benchmarks(indicators):
    """Unweighted median across Hawai'i census tracts."""

    return {
        "median_income": indicators["median_income"].median(),
        "renter_burden_pct": indicators["renter_burden_pct"].median(),
        "no_internet_pct": indicators["no_internet_pct"].median()
    }


def prioritize_needs(profiles, benchmarks, chamber="House"):
    """Rank community needs for the selected legislative chamber."""
    if chamber not in ("House", "Senate"):
        raise ValueError("Chamber must be House or Senate.")
    district_column = chamber.lower() + "_district"
    district_label = chamber + " District"

    categories = [
        ("median_income", "Income and Economic Opportunity", "lower"),
        ("renter_burden_pct", "Housing Affordability", "higher"),
        ("no_internet_pct", "Digital Access", "higher")
    ]

    findings = []

    for _, district in profiles.iterrows():
        district_id = str(district[district_column]).zfill(3)

        for column, category, direction in categories:
            value = district[column]
            benchmark = benchmarks[column]

            if (
                pd.isna(value)
                or pd.isna(benchmark)
                or benchmark <= 0
            ):
                severity = "Insufficient Data"
                difference_pct = float("nan")
                priority_rank = 99

            else:
                if direction == "lower":
                    difference_pct = (
                        (benchmark - value) / benchmark * 100
                    )
                else:
                    difference_pct = (
                        (value - benchmark) / benchmark * 100
                    )

                if difference_pct >= 20:
                    severity = "Elevated"
                    priority_rank = 1
                elif difference_pct >= 10:
                    severity = "Moderate"
                    priority_rank = 2
                else:
                    severity = "Baseline"
                    priority_rank = 3

            findings.append({
                district_label: district_id,
                "Community Need": category,
                "District Value": value,
                "Statewide Benchmark": benchmark,
                "Difference (%)": difference_pct,
                "Priority": severity,
                "Priority Rank": priority_rank
            })

    results = pd.DataFrame(findings)

    return results.sort_values(
        [district_label, "Priority Rank", "Difference (%)"],
        ascending=[True, True, False],
        na_position="last"
    ).reset_index(drop=True)


# Initial reference catalog. Program details and eligibility
# must be verified against current official sources.
ASSISTANCE_PROGRAMS = [
    {
        "name": "Supplemental Nutrition Assistance Program (SNAP)",
        "category": "Income and Economic Opportunity",
        "agency": "Hawaii Department of Human Services",
        "website": "https://humanservices.hawaii.gov/bessd/snap/",
        "description": "Food assistance for eligible households."
    },
    {
        "name": "Temporary Assistance for Needy Families (TANF)",
        "category": "Income and Economic Opportunity",
        "agency": "Hawaii Department of Human Services",
        "website": "https://humanservices.hawaii.gov/",
        "description": "Potential cash and employment-related assistance."
    },
    {
        "name": "Housing Choice Voucher Program (Section 8)",
        "category": "Housing Affordability",
        "agency": "Hawaii Public Housing Authority",
        "website": "https://hpha.hawaii.gov/",
        "description": "Rental assistance for qualifying households."
    },
    {
        "name": "Low Income Home Energy Assistance Program (LIHEAP)",
        "category": "Housing Affordability",
        "agency": "Hawaii Department of Human Services",
        "website": "https://humanservices.hawaii.gov/",
        "description": "Assistance with qualifying household energy costs."
    },
    {
        "name": "Lifeline",
        "category": "Digital Access",
        "agency": "Federal Communications Commission",
        "website": "https://www.lifelinesupport.org/",
        "description": "Discounted qualifying phone or internet service."
    }
]


def match_assistance_programs(
    priorities, include_baseline=False, chamber="House"
):
    """Match community needs to programs for either chamber."""
    if chamber not in ("House", "Senate"):
        raise ValueError("Chamber must be House or Senate.")
    district_label = chamber + " District"

    matches = []

    for _, finding in priorities.iterrows():
        priority = finding["Priority"]

        if priority == "Insufficient Data":
            continue

        if priority == "Baseline" and not include_baseline:
            continue

        for program in ASSISTANCE_PROGRAMS:
            if program["category"] != finding["Community Need"]:
                continue

            matches.append({
                district_label: finding[district_label],
                "Community Need": finding["Community Need"],
                "Priority": priority,
                "Program": program["name"],
                "Agency": program["agency"],
                "Description": program["description"],
                "Official Website": program["website"],
                "Why Relevant": (
                    f"{program['name']} addresses the "
                    f"{finding['Community Need']} category. "
                    f"The district has a community priority of {priority.lower()} "
                    "under the prototype tract-based screening method. "
                    "This does not establish individual eligibility."
                ),
                "Screening Guidance": (
                    "Confirm current eligibility, application instructions "
                    "and availability with the administering agency."
                ),
                "Eligibility": "Not determined - individual screening required"
            })

    return pd.DataFrame(matches)
