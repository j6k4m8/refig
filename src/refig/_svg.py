"""Helpers for embedding and extracting metadata in SVG files."""

from __future__ import annotations

import html
import json
import re
from typing import Any

_METADATA_PATTERN = re.compile(
    r"<metadata\b[^>]*\bid=(?P<quote>['\"])refig(?P=quote)[^>]*>(?P<body>.*?)</metadata>",
    flags=re.DOTALL | re.IGNORECASE,
)
_SVG_OPEN_TAG_PATTERN = re.compile(r"<svg\b[^>]*>", flags=re.IGNORECASE)


class SVGMetadataError(RuntimeError):
    """Raised when metadata cannot be embedded or extracted."""


def embed_metadata(svg_bytes: bytes, metadata: dict[str, Any]) -> bytes:
    """Embed metadata into an SVG byte-string inside a <metadata> tag."""
    try:
        text = svg_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SVGMetadataError("SVG data is not valid UTF-8.") from exc

    payload = json.dumps(metadata, separators=(",", ":"), sort_keys=True)
    escaped_payload = html.escape(payload)

    match = _METADATA_PATTERN.search(text)
    if match:
        start, end = match.span("body")
        text = text[:start] + escaped_payload + text[end:]
    else:
        svg_match = _SVG_OPEN_TAG_PATTERN.search(text)
        if not svg_match:
            raise SVGMetadataError("Unable to locate <svg> root element in SVG document.")
        insert = f"\n  <metadata id=\"refig\">{escaped_payload}</metadata>\n"
        index = svg_match.end()
        text = text[:index] + insert + text[index:]

    return text.encode("utf-8")


def extract_metadata(svg_bytes: bytes) -> dict[str, Any]:
    """Extract metadata from an SVG byte-string."""
    try:
        text = svg_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SVGMetadataError("SVG data is not valid UTF-8.") from exc

    match = _METADATA_PATTERN.search(text)
    if not match:
        raise SVGMetadataError("No refig metadata found in the provided SVG.")

    payload = html.unescape(match.group("body")).strip()
    if not payload:
        raise SVGMetadataError("Refig metadata block is empty.")

    return json.loads(payload)
