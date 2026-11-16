import pandas as pd


def normalize_tract(value):
    """Return an 11-digit tract GEOID or None."""
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    if not text.isdigit() or len(text) != 11:
        return None

    return text


def normalize_district(value):
    """Return a three-digit Hawai?i House district or None."""
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    if not text.isdigit():
        return None

    number = int(text)

    if not 1 <= number <= 51:
        return None

    return f"{number:03d}"


def validate_geography(
    imported_frame,
    reference_tracts,
    reference_districts,
    crosswalk
):
    """Validate external tract/district relationships.

    No imported values are merged into reference datasets.
    """

    required = {"tract_geoid", "house_district"}

    if not required.issubset(imported_frame.columns):
        missing = sorted(required - set(imported_frame.columns))
        raise ValueError(
            "Required geographic columns missing: "
            + ", ".join(missing)
        )

    if not {"tract_geoid", "house_district"}.issubset(
        crosswalk.columns
    ):
        raise ValueError(
            "Reference crosswalk is missing required columns."
        )

    valid_tracts = {
        tract
        for value in reference_tracts
        if (tract := normalize_tract(value)) is not None
    }

    valid_districts = {
        district
        for value in reference_districts
        if (district := normalize_district(value)) is not None
    }

    valid_relationships = set()

    for tract, district in zip(
        crosswalk["tract_geoid"],
        crosswalk["house_district"]
    ):
        tract_id = normalize_tract(tract)
        district_id = normalize_district(district)

        if tract_id and district_id:
            valid_relationships.add(
                (tract_id, district_id)
            )

    results = imported_frame.copy()

    statuses = []
    explanations = []

    for _, record in results.iterrows():
        raw_tract = record["tract_geoid"]
        raw_district = record["house_district"]

        tract = normalize_tract(raw_tract)
        district = normalize_district(raw_district)

        tract_missing = (
            pd.isna(raw_tract)
            or str(raw_tract).strip() == ""
        )

        district_missing = (
            pd.isna(raw_district)
            or str(raw_district).strip() == ""
        )

        if tract_missing or district_missing:
            status = "REVIEW"
            explanation = "Missing geographic identifier."

        elif tract is None or district is None:
            status = "INVALID"
            explanation = "Malformed tract or district identifier."

        elif tract not in valid_tracts:
            status = "INVALID"
            explanation = "Census tract not found in reference data."

        elif district not in valid_districts:
            status = "INVALID"
            explanation = "House district not found in reference data."

        elif (tract, district) not in valid_relationships:
            status = "INVALID"
            explanation = (
                "Tract does not overlap the claimed House district."
            )

        else:
            status = "VALID"
            explanation = "Geographic relationship verified."

        statuses.append(status)
        explanations.append(explanation)

    results["Geographic Status"] = statuses
    results["Geographic Explanation"] = explanations

    summary = {
        "Total Records": len(results),
        "Valid": statuses.count("VALID"),
        "Review": statuses.count("REVIEW"),
        "Invalid": statuses.count("INVALID")
    }

    return results, summary
