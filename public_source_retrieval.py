"""Retrieve public source text from an explicitly approved website."""

import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urlsplit

import requests

MAX_BYTES = 2 * 1024 * 1024

APPROVED_DOMAINS = (
    "census.gov",
    "hawaii.gov",
    "congress.gov",
)

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        if not self.skip_depth:
            clean = " ".join(data.split())
            if clean:
                self.parts.append(clean)

def validate_public_url(url):
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower().rstrip(".")

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS websites are supported.")

    if parsed.username or parsed.password:
        raise ValueError("Embedded credentials are not permitted.")

    if parsed.port not in (None, 443):
        raise ValueError("Nonstandard ports are not permitted.")

    if not any(
        host == domain or host.endswith("." + domain)
        for domain in APPROVED_DOMAINS
    ):
        raise ValueError("Website is not on the approved public-source list.")

    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)

    for entry in addresses:
        address = ipaddress.ip_address(entry[4][0])
        if not address.is_global:
            raise ValueError("Website resolves to a nonpublic address.")

    return parsed.geturl()

def retrieve_public_text(url):
    validated = validate_public_url(url)

    response = requests.get(
        validated,
        timeout=(5, 20),
        allow_redirects=False,
        stream=True,
        headers={
            "User-Agent": "DeepBet-SourceIntelligence/0.1",
            "Accept": "text/html, text/plain"
        }
    )

    try:
        if 300 <= response.status_code < 400:
            raise ValueError("Website redirected. Use its final HTTPS URL.")

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if not (
            "text/html" in content_type or
            "text/plain" in content_type
        ):
            raise ValueError("Source is not an HTML or plain-text page.")

        data = bytearray()

        for chunk in response.iter_content(chunk_size=8192):
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError("Website response exceeds 2 MB.")

        encoding = response.encoding or "utf-8"
        raw = bytes(data).decode(encoding, errors="replace")

        if "text/html" in content_type:
            parser = TextExtractor()
            parser.feed(raw)
            text = "\n".join(parser.parts)
        else:
            text = raw

        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if not text:
            raise ValueError("No readable text found on the website.")

        return {
            "url": validated,
            "text": text[:100000],
            "characters": len(text),
            "status": "Retrieved; content not independently verified"
        }
    finally:
        response.close()
