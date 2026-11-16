"""Source Intelligence: transparent numerical fact extraction.

This is rule-based extraction, not an AI language model.
Source statements remain unverified until independently checked.
"""

import re
import pandas as pd

MAX_TEXT_LENGTH = 100_000
MAX_FINDINGS = 200

NUMBER_PATTERN = re.compile(
    r"(?<![\w.])"
    r"(?P<value>\$?\d[\d,]*(?:\.\d+)?)"
    r"(?P<percent>\s*%)?"
)

def extract_source_facts(text, source_name="User-provided text",
                         source_url=""):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Source text cannot be empty.")

    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError("Source text exceeds 100,000 characters.")

    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    findings = []

    for sentence in sentences:
        sentence = " ".join(sentence.split())
        if not sentence:
            continue

        for match in NUMBER_PATTERN.finditer(sentence):
            raw = match.group("value")
            is_percent = bool(match.group("percent"))
            clean = raw.replace("$", "").replace(",", "")

            try:
                value = float(clean)
            except ValueError:
                continue

            prefix = sentence[max(0, match.start() - 70):match.start()]
            suffix = sentence[match.end():match.end() + 70]

            classification = (
                "Percentage" if is_percent
                else "Monetary value" if raw.startswith("$")
                else "Possible year" if (
                    value.is_integer() and 1900 <= value <= 2100
                )
                else "General number"
            )

            findings.append({
                "Classification": classification,
                "Source": source_name,
                "Source URL": source_url,
                "Value": value,
                "Unit": (
                    "percent" if is_percent
                    else "USD" if raw.startswith("$")
                    else "number"
                ),
                "Context Before": prefix.strip(),
                "Context After": suffix.strip(),
                "Evidence": sentence[:1000],
                "Verification": "Unverified extraction"
            })

            if len(findings) >= MAX_FINDINGS:
                break

        if len(findings) >= MAX_FINDINGS:
            break

    columns = [
        "Classification", "Source", "Source URL", "Value", "Unit",
        "Context Before", "Context After",
        "Evidence", "Verification"
    ]

    return pd.DataFrame(findings, columns=columns)
