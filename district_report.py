
"""Printable, locally generated legislative district reports."""

from io import BytesIO
from html import escape
import math

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

from demographic_engine import calculate_demographics


def _text(value):
    if value is None:
        return "Unavailable"
    try:
        if math.isnan(float(value)):
            return "Unavailable"
    except (ValueError, TypeError, OverflowError):
        pass
    return str(value)


def _p(value, style):
    return Paragraph(escape(_text(value)), style)


def _number(value, prefix="", suffix="", decimals=0):
    try:
        value = float(value)
        if not math.isfinite(value) or value < 0:
            return "Unavailable"
        return prefix + f"{value:,.{decimals}f}" + suffix
    except (TypeError, ValueError, OverflowError):
        return "Unavailable"


def _official_data(row):
    if row is None:
        return {}, None

    raw = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    translated = {}
    for key, value in raw.items():
        if "_E" in key:
            table, number = key.split("_E", 1)
            if table in ("B01001", "B17001", "B23025", "C24030"):
                translated[f"{table}_{number}E"] = value

    demographics = calculate_demographics(translated)

    try:
        income = int(raw.get("B19013_E001"))
        if income < 0:
            income = None
    except (ValueError, TypeError):
        income = None

    return demographics, income


def generate_district_pdf(
    chamber, district, profile, official_row, priorities, programs
):
    """Return PDF bytes for one selected legislative district."""
    if chamber not in ("House", "Senate"):
        raise ValueError("Unsupported legislative chamber")

    district = str(district).zfill(3)
    demographics, income = _official_data(official_row)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(8.5 * inch, 11 * inch),
        rightMargin=40,
        leftMargin=40,
        topMargin=38,
        bottomMargin=38,
        title=f"Hawaii {chamber} District {district} Profile",
        author="Project Deep Bet - Team Veritas",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DBTitle", parent=styles["Title"],
        fontSize=17, leading=21, alignment=TA_CENTER,
        textColor=colors.HexColor("#15334B"), spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="DBSmall", parent=styles["BodyText"],
        fontSize=8, leading=11, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="DBCell", parent=styles["BodyText"],
        fontSize=8, leading=10,
    ))
    styles.add(ParagraphStyle(
        name="DBHeading", parent=styles["Heading2"],
        fontSize=10, leading=13, spaceBefore=10, spaceAfter=5,
        textColor=colors.HexColor("#15334B"),
    ))

    story = []
    small = styles["DBSmall"]
    cell = styles["DBCell"]

    def paragraph(value):
        story.append(_p(value, small))

    def heading(value):
        story.append(_p(value, styles["DBHeading"]))

    def table(headers, rows, widths):
        cells = [[_p(h, cell) for h in headers]]
        for row in rows:
            cells.append([_p(v, cell) for v in row])

        t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F4F7FA")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ]))
        story.append(t)

    story.append(_p(
        f"Hawaii {chamber} District {district}",
        styles["DBTitle"],
    ))
    paragraph("PROJECT DEEP BET | TEAM VERITAS | HAIC 2026")
    paragraph("Nonpartisan district profile | ACS 2024 five-year estimates")

    heading("Official District Demographics")
    if official_row is None:
        paragraph("Official district demographics unavailable.")
    else:
        metrics = [
            ("Population", _number(demographics.get("population"))),
            ("Under age 18", _number(
                demographics.get("children_under_18_pct"), suffix="%", decimals=1
            )),
            ("Age 65 and older", _number(
                demographics.get("kupuna_65_plus_pct"), suffix="%", decimals=1
            )),
            ("Median household income", _number(income, prefix="$")),
            ("Poverty rate", _number(
                demographics.get("poverty_rate_pct"), suffix="%", decimals=1
            )),
            ("Civilian unemployment rate", _number(
                demographics.get("unemployment_rate_pct"), suffix="%", decimals=1
            )),
            ("Employed residents (industry table)", _number(
                demographics.get("industry_employed_total")
            )),
        ]
        table(["Indicator", "2024 ACS estimate"], metrics, [265, 240])

        industries = [
            (name, _number(values.get("count")))
            for name, values in demographics.get("industries", {}).items()
            if values.get("count") is not None
        ]
        industries.sort(
            key=lambda item: float(item[1].replace(",", ""))
            if item[1] != "Unavailable" else -1,
            reverse=True,
        )
        if industries:
            heading("Leading Employment Industries")
            table(
                ["Industry", "Employed residents"],
                industries[:5], [365, 140],
            )

    heading("Overlapping-Tract Indicators")
    tract_rows = [
        ("Overlapping census tracts", _number(profile.get("tract_count"))),
        ("Median of tract median incomes", _number(
            profile.get("median_income"), prefix="$", decimals=2
        )),
        ("Median tract renter cost burden", _number(
            profile.get("renter_burden_pct"), suffix="%", decimals=1
        )),
        ("Median tract without internet", _number(
            profile.get("no_internet_pct"), suffix="%", decimals=1
        )),
    ]
    table(["Prototype indicator", "Value"], tract_rows, [265, 240])
    paragraph(
        "These indicators are unweighted medians of overlapping census "
        "tracts. They are not official district-level population estimates."
    )

    heading("Community Needs Assessment")
    if priorities is None or priorities.empty:
        paragraph("No community priority records available.")
    else:
        rows = []
        for _, item in priorities.iterrows():
            need = str(item.get("Community Need", ""))
            value = item.get("District Value")

            if need == "Income and Economic Opportunity":
                formatted_value = _number(
                    value, prefix="$", decimals=2
                )
            elif need in ("Digital Access", "Housing Affordability"):
                formatted_value = _number(
                    value, suffix="%", decimals=1
                )
            else:
                formatted_value = _text(value)

            rows.append((
                need,
                item.get("Priority"),
                formatted_value,
            ))
        table(["Community need", "Priority", "Prototype value"],
              rows, [215, 125, 165])

    heading("Potential Assistance Programs")
    if programs is None or programs.empty:
        paragraph("No programs matched the current prototype priorities.")
    else:
        for _, item in programs.iterrows():
            story.append(KeepTogether([
                _p(item.get("Program"), styles["Heading3"]),
                _p(
                    "Agency: " + _text(item.get("Agency")),
                    small,
                ),
                _p(
                    "Relevance: " + _text(item.get("Why Relevant")),
                    small,
                ),
                _p(
                    "Next step: " + _text(item.get("Screening Guidance")),
                    small,
                ),
                _p(
                    "Official website: " + _text(item.get("Official Website")),
                    small,
                ),
                Spacer(1, 5),
            ]))

    heading("Sources and Limitations")
    for note in (
        "U.S. Census Bureau, 2024 American Community Survey, "
        "five-year estimates (2020-2024), including legislative "
        "district summary tables.",
        "U.S. Census Bureau, 2025 TIGER/Line legislative district "
        "and census tract geographic boundaries.",
        "ACS figures are estimates subject to sampling uncertainty. "
        "Percentage margins of error are not calculated in this report.",
        "Community priorities are prototype classifications using "
        "statewide tract-median benchmarks, not official standards.",
        "Geographic tract overlap does not imply population weighting. "
        "Area fractions are not population fractions.",
        "Program matching does not establish individual eligibility "
        "or guarantee funding or availability. Confirm with the agency.",
        "Local dataset structural checks do not constitute independent "
        "reconciliation with original government releases.",
    ):
        paragraph(note)

    paragraph(
        "Source reference: https://www.census.gov/programs-surveys/acs"
    )
    paragraph(
        "Boundary reference: https://www.census.gov/geographies/mapping-files/"
        "time-series/geo/tiger-line-file.html"
    )

    doc.build(story)
    result = buffer.getvalue()
    if not result.startswith(b"%PDF-"):
        raise RuntimeError("PDF generation failed")
    return result
