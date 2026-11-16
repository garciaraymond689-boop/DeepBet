import re
import pandas as pd


SOURCE_NOTE = (
    "Source: 2024 U.S. Census Bureau American Community Survey "
    "tract-level data, summarized using the project's "
    "tract-to-House-district crosswalk. District figures are "
    "unweighted medians across overlapping tracts, not official "
    "district-level population estimates. Margins of error are "
    "not included."
)


def answer_district_question(question, district, profiles, programs):
    """Answer supported questions using existing district data only."""

    query = (question or "").strip().lower()
    district = str(district).zfill(3)

    if not query:
        return "Enter a question about income, housing, internet access, or assistance programs."

    row = profiles.loc[
        profiles["house_district"].astype(str).str.zfill(3) == district
    ]

    if row.empty:
        return f"No district profile is available for House District {district}."

    profile = row.iloc[0]

    def fmt_number(column, kind):
        value = pd.to_numeric(profile[column], errors="coerce")
        if pd.isna(value):
            return "Data unavailable"
        if kind == "money":
            return f"${value:,.0f}"
        return f"{value:.1f}%"

    heading = f"House District {district}"

    if re.search(r"\b(income|earnings|salary|wages)\b", query):
        return (
            f"{heading}: The median of overlapping census tracts' "
            f"median household incomes is "
            f"{fmt_number('median_income', 'money')}. "
            f"This is not the district's median household income.\n\n"
            f"{SOURCE_NOTE}"
        )

    if re.search(r"\b(rent|renter|housing|affordab|cost burden)\w*", query):
        return (
            f"{heading}: The median tract-level share of renters "
            f"experiencing a housing cost burden is "
            f"{fmt_number('renter_burden_pct', 'percent')}. "
            f"This is not a population-weighted district rate.\n\n"
            f"{SOURCE_NOTE}"
        )

    if re.search(r"\b(internet|broadband|digital|connectivity)\b", query):
        return (
            f"{heading}: The median tract-level share of households "
            f"without an internet subscription is "
            f"{fmt_number('no_internet_pct', 'percent')}. "
            f"This is not a population-weighted district rate.\n\n"
            f"{SOURCE_NOTE}"
        )

    if re.search(r"\b(program|benefit|assistance|help|support)\w*", query):
        district_programs = programs.loc[
            programs["House District"].astype(str).str.zfill(3)
            == district
        ]

        if district_programs.empty:
            return (
                f"{heading}: No programs were matched by the current "
                "prototype priority thresholds. This does not mean "
                "residents lack eligibility for assistance."
            )

        lines = [
            f"{heading}: Potentially relevant assistance programs:"
        ]

        for _, item in district_programs.drop_duplicates(
            subset=["Program"]
        ).iterrows():
            lines.append(
                f"- {item['Program']} — {item['Official Website']}"
            )

        lines.append(
            "\nThese are informational matches, not eligibility "
            "determinations. Confirm current requirements with "
            "each administering agency."
        )

        return "\n".join(lines)

    return (
        "I don't have enough verified data to answer that question. "
        "Currently supported topics are household income, housing "
        "cost burden, internet access, and assistance programs. "
        "I won't invent figures or make claims about individual residents."
    )
