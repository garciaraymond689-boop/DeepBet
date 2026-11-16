import io
import pandas as pd


def inspect_csv(file_bytes):
    """Inspect an external CSV without modifying existing datasets."""

    if len(file_bytes) > 10 * 1024 * 1024:
        raise ValueError("CSV exceeds the 10 MB upload limit.")

    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    try:
        frame = pd.read_csv(
            io.BytesIO(file_bytes),
            dtype=str,
            encoding="utf-8-sig",
            on_bad_lines="error"
        )
    except Exception as error:
        raise ValueError(
            f"Unable to read CSV: {error}"
        ) from error

    if frame.empty:
        raise ValueError("CSV contains no data rows.")

    if len(frame.columns) > 100:
        raise ValueError("CSV contains more than 100 columns.")

    columns = [str(column).strip() for column in frame.columns]

    if len(set(columns)) != len(columns):
        raise ValueError("CSV contains duplicate column names.")

    frame.columns = columns

    possible_geo_columns = [
        column for column in columns
        if any(
            term in column.lower()
            for term in [
                "geoid",
                "tract",
                "district",
                "county",
                "zip",
                "fips"
            ]
        )
    ]

    report = {
        "Rows": len(frame),
        "Columns": len(frame.columns),
        "Duplicate Rows": int(frame.duplicated().sum()),
        "Missing Cells": int(frame.isna().sum().sum()),
        "Possible Geographic Columns": possible_geo_columns,
        "Column Names": columns
    }

    return frame, report
