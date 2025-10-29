"""Public interface for the refig library."""

from __future__ import annotations

import os
from typing import Any

from ._core import SaveResult, load_metadata, savefig

PathLike = os.PathLike[Any]


class _RefigAPI:
    """Lightweight namespace exposing the public API."""

    def savefig(self, name: str, **kwargs):
        """Proxy to :func:`savefig`."""
        return savefig(name, **kwargs)

    def meta(self, path: str | bytes | PathLike):
        """Proxy to :func:`load_metadata`."""
        return load_metadata(path)


refig = _RefigAPI()

__all__ = ["refig", "savefig", "load_metadata", "SaveResult"]
