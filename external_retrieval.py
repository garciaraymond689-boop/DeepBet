import io
import ipaddress
import socket
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pandas as pd
import requests


APPROVED_HOSTS = {
    "api.census.gov"
}

MAX_RESPONSE_BYTES = 10 * 1024 * 1024


def validate_source_url(url):
    """Check an external URL against the approved-source policy."""

    if not isinstance(url, str):
        raise ValueError("Source URL must be text.")

    parsed = urlsplit(url.strip())

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS sources are permitted.")

    if parsed.hostname not in APPROVED_HOSTS:
        raise ValueError(
            "Source host is not on the approved list."
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "Credentials embedded in URLs are not permitted."
        )

    if parsed.port not in (None, 443):
        raise ValueError("Nonstandard ports are not permitted.")

    if parsed.fragment:
        raise ValueError("URL fragments are not permitted.")

    return parsed.geturl()


def retrieve_census_data(url):
    """Retrieve structured Census API data without merging it."""

    validated_url = validate_source_url(url)

    try:
        response = requests.get(
            validated_url,
            timeout=(5, 20),
            allow_redirects=False,
            stream=True,
            headers={
                "Accept": "application/json"
            }
        )

        with response:
            if 300 <= response.status_code < 400:
                raise ValueError(
                    "Redirects are not permitted."
                )

            response.raise_for_status()

            chunks = []
            total = 0

            for chunk in response.iter_content(
                chunk_size=65536
            ):
                if not chunk:
                    continue

                total += len(chunk)

                if total > MAX_RESPONSE_BYTES:
                    raise ValueError(
                        "Response exceeds the 10 MB limit."
                    )

                chunks.append(chunk)

            payload = b"".join(chunks)

    except requests.RequestException as error:
        raise ValueError(
            f"External retrieval failed: {error}"
        ) from error

    try:
        import json
        records = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as error:
        raise ValueError(
            "Source did not return valid JSON."
        ) from error

    if (
        not isinstance(records, list)
        or len(records) < 2
        or not isinstance(records[0], list)
    ):
        raise ValueError(
            "Unexpected Census API response structure."
        )

    headers = records[0]
    rows = records[1:]

    if (
        len(headers) > 100
        or any(
            not isinstance(row, list)
            or len(row) != len(headers)
            for row in rows
        )
    ):
        raise ValueError(
            "Invalid Census API table structure."
        )

    frame = pd.DataFrame(rows, columns=headers)

    metadata = {
        "Source URL": validated_url,
        "Retrieved UTC": datetime.now(
            timezone.utc
        ).isoformat(),
        "Records": len(frame),
        "Columns": len(frame.columns),
        "Source Verified": False,
        "Retrieval Status": "SUCCESS"
    }

    return frame, metadata
