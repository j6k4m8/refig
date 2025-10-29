"""Helpers for embedding and extracting metadata in PNG files."""

from __future__ import annotations

import json
import struct
import zlib
from typing import Any

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_METADATA_KEYWORD = "refig"


class PNGMetadataError(RuntimeError):
    """Raised when metadata cannot be embedded or extracted."""


def embed_metadata(png_bytes: bytes, metadata: dict[str, Any]) -> bytes:
    """Embed metadata into a PNG byte-string using a tEXt chunk."""
    if not png_bytes.startswith(PNG_SIGNATURE):
        raise PNGMetadataError("Input data does not look like a PNG image.")

    payload = json.dumps(metadata, separators=(",", ":"), sort_keys=True)
    chunk = _build_text_chunk(_METADATA_KEYWORD, payload)
    return PNG_SIGNATURE + chunk + png_bytes[len(PNG_SIGNATURE) :]


def extract_metadata(png_bytes: bytes) -> dict[str, Any]:
    """Extract metadata from a PNG byte-string."""
    if not png_bytes.startswith(PNG_SIGNATURE):
        raise PNGMetadataError("Input data does not look like a PNG image.")

    chunks = _iter_chunks(png_bytes)
    for chunk_type, chunk_data in chunks:
        if chunk_type == b"tEXt":
            keyword, text = _split_text_chunk(chunk_data)
            if keyword == _METADATA_KEYWORD:
                return json.loads(text)
    raise PNGMetadataError("No refig metadata found in the provided image.")


def _build_text_chunk(keyword: str, text: str) -> bytes:
    keyword_bytes = keyword.encode("latin-1")
    text_bytes = text.encode("utf-8")
    chunk_data = keyword_bytes + b"\x00" + text_bytes
    chunk_type = b"tEXt"
    length = struct.pack(">I", len(chunk_data))
    crc = struct.pack(">I", zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
    return length + chunk_type + chunk_data + crc


def _split_text_chunk(chunk_data: bytes) -> tuple[str, str]:
    keyword, _, text = chunk_data.partition(b"\x00")
    if not keyword:
        raise PNGMetadataError("Invalid tEXt chunk encountered.")
    return keyword.decode("latin-1"), text.decode("utf-8")


def _iter_chunks(png_bytes: bytes):
    index = len(PNG_SIGNATURE)
    length_bytes = png_bytes[index : index + 4]
    while length_bytes:
        length = struct.unpack(">I", length_bytes)[0]
        index += 4
        chunk_type = png_bytes[index : index + 4]
        index += 4
        chunk_data = png_bytes[index : index + length]
        index += length
        # skip CRC
        index += 4
        yield chunk_type, chunk_data
        if index >= len(png_bytes):
            break
        length_bytes = png_bytes[index : index + 4]
