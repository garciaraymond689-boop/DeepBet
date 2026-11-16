"""Structural validation and source inventory for Deep Bet.

These checks do not independently authenticate downloaded data.
"""

import csv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DATASETS = (
    ("Legislative district ACS", "data/demographics/hawaii_legislative_districts_acs2024.csv", "2024 ACS 5-year", "House and Senate districts", "CSV"),
    ("Statewide ACS", "data/demographics/hawaii_statewide_acs2024.csv", "2024 ACS 5-year", "Hawaii statewide", "CSV"),
    ("Tract income", "data/demographics/hawaii_income_2024.csv", "2024 ACS 5-year", "Census tracts", "CSV"),
    ("Tract housing", "data/demographics/hawaii_housing_2024.csv", "2024 ACS 5-year", "Census tracts", "CSV"),
    ("Tract homeowners", "data/demographics/hawaii_homeowners_2024.csv", "2024 ACS 5-year", "Census tracts", "CSV"),
    ("Tract internet", "data/demographics/hawaii_internet_2024.csv", "2024 ACS 5-year", "Census tracts", "CSV"),
    ("Census tract boundaries", "data/boundaries/hawaii_census_tracts.zip", "2025 TIGER/Line", "Census tracts", "ZIP"),
    ("House boundaries", "data/boundaries/hawaii_house_districts.zip", "2025 TIGER/Line", "House districts", "ZIP"),
    ("Senate boundaries", "data/boundaries/hawaii_senate_districts.zip", "2025 TIGER/Line", "Senate districts", "ZIP"),
)

def inspect_sources(root=ROOT):
    root = Path(root)
    results = []

    for name, relative, vintage, geography, kind in DATASETS:
        path = root / relative
        item = {
            "Dataset": name,
            "Local File": relative,
            "Source Family": "U.S. Census Bureau",
            "Vintage": vintage,
            "Geography": geography,
            "Status": "PASS",
            "Details": "",
            "Verification Level": "Local structural checks only",
        }

        if not path.is_file():
            item["Status"] = "FAIL"
            item["Details"] = "Missing local file"
            results.append(item)
            continue

        try:
            if kind == "ZIP":
                with zipfile.ZipFile(path) as archive:
                    names = archive.namelist()
                    if not names or archive.testzip() is not None:
                        raise ValueError("Invalid ZIP archive")
                    item["Details"] = f"{len(names)} archive entries"

            else:
                with path.open(
                    newline="", encoding="utf-8-sig"
                ) as handle:
                    reader = csv.DictReader(handle)
                    fields = reader.fieldnames or []
                    rows = list(reader)

                if not fields or not rows:
                    raise ValueError("Empty or malformed CSV")

                item["Details"] = (
                    f"{len(rows)} rows; {len(fields)} columns"
                )

                if name in (
                    "Legislative district ACS",
                    "Statewide ACS",
                ):
                    estimates = [
                        field for field in fields
                        if "_E" in field
                    ]
                    margins = [
                        field for field in fields
                        if "_M" in field
                    ]

                    if not estimates or not margins:
                        raise ValueError("Missing ACS estimates or MOEs")

                    item["Details"] += (
                        f"; {len(estimates)} estimate columns"
                        f"; {len(margins)} MOE columns"
                    )

                    if name == "Legislative district ACS":
                        keys = [
                            (r.get("chamber"), r.get("district"))
                            for r in rows
                        ]

                        expected = {
                            ("House", f"{i:03d}")
                            for i in range(1, 52)
                        } | {
                            ("Senate", f"{i:03d}")
                            for i in range(1, 26)
                        }

                        if (
                            len(keys) != 76
                            or set(keys) != expected
                        ):
                            raise ValueError(
                                "Legislative district coverage mismatch"
                            )

                    if name == "Statewide ACS":
                        if (
                            len(rows) != 1
                            or rows[0].get("GEO_ID")
                            != "0400000US15"
                        ):
                            raise ValueError(
                                "Statewide geography mismatch"
                            )

        except (
            OSError,
            ValueError,
            csv.Error,
            zipfile.BadZipFile,
        ) as error:
            item["Status"] = "FAIL"
            item["Details"] = str(error)

        results.append(item)

    return results


if __name__ == "__main__":
    results = inspect_sources()

    for item in results:
        print(
            f"{item['Status']}: {item['Dataset']} | "
            f"{item['Details']}"
        )

    failures = [
        item for item in results
        if item["Status"] != "PASS"
    ]

    print(
        f"\nLocal structural checks: "
        f"{len(results) - len(failures)}/{len(results)}"
    )
    print("Independent source reconciliation: NOT PERFORMED")

    if failures:
        raise SystemExit(1)
