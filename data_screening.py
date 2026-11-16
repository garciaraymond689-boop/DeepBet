import re
import pandas as pd


def screen_external_data(frame):
    """Screen external data without modifying the original."""

    if frame.empty:
        raise ValueError("Dataset contains no records.")

    findings = []
    total_rows = len(frame)

    def add(category, status, detail):
        findings.append({
            "Category": category,
            "Status": status,
            "Finding": detail
        })

    # Completeness
    missing = int(frame.isna().sum().sum())
    duplicates = int(frame.duplicated().sum())

    add(
        "Completeness",
        "PASS" if missing == 0 else "REVIEW",
        f"{missing} missing cells detected."
    )

    add(
        "Duplicates",
        "PASS" if duplicates == 0 else "REVIEW",
        f"{duplicates} duplicate rows detected."
    )

    # Source identification
    if "source_name" in frame.columns:
        sources = (
            frame["source_name"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        sources = sources[sources != ""]

        add(
            "Source Identification",
            "REVIEW" if len(sources) else "FAIL",
            (
                f"{sources.nunique()} source name(s) declared. "
                "Source authenticity has not been independently verified."
            ) if len(sources) else "No usable source name supplied."
        )
    else:
        add(
            "Source Identification",
            "FAIL",
            "No source_name column supplied."
        )

    # Reporting year
    if "report_year" in frame.columns:
        years = pd.to_numeric(
            frame["report_year"],
            errors="coerce"
        )

        invalid_years = int(
            (
                years.isna()
                | (years < 2000)
                | (years > 2026)
            ).sum()
        )

        add(
            "Reporting Year",
            "PASS" if invalid_years == 0 else "REVIEW",
            f"{invalid_years} missing or out-of-range reporting years."
        )
    else:
        add(
            "Reporting Year",
            "REVIEW",
            "No report_year column supplied."
        )

    # Known numeric indicators
    numeric_columns = [
        "reported_cases",
        "estimated_households"
    ]

    for column in numeric_columns:
        if column not in frame.columns:
            continue

        values = pd.to_numeric(
            frame[column],
            errors="coerce"
        )

        missing_values = frame[column].isna() | (
            frame[column].astype(str).str.strip() == ""
        )

        invalid = (
            (~missing_values & values.isna())
            | (values < 0)
            | (values.notna() & (values % 1 != 0))
        )

        invalid_count = int(invalid.sum())

        add(
            f"Numeric: {column}",
            "PASS" if invalid_count == 0 else "FAIL",
            f"{invalid_count} invalid numeric values."
        )

    if {
        "reported_cases",
        "estimated_households"
    }.issubset(frame.columns):

        cases = pd.to_numeric(
            frame["reported_cases"],
            errors="coerce"
        )
        households = pd.to_numeric(
            frame["estimated_households"],
            errors="coerce"
        )

        excessive = int(
            (
                cases.notna()
                & households.notna()
                & (cases > households)
            ).sum()
        )

        add(
            "Cases vs. Households",
            "REVIEW" if excessive else "PASS",
            (
                f"{excessive} records have more reported cases "
                "than estimated households. Review whether these "
                "fields represent comparable units."
            )
        )

    report = pd.DataFrame(findings)

    return report, {
        "Records": total_rows,
        "Passed Checks": int((report["Status"] == "PASS").sum()),
        "Review Checks": int((report["Status"] == "REVIEW").sum()),
        "Failed Checks": int((report["Status"] == "FAIL").sum()),
        "Source Verified": False
    }
