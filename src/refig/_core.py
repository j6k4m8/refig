"""Core logic for the refig library."""

from __future__ import annotations

import io
import subprocess
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ._png import PNGMetadataError, PNG_SIGNATURE, embed_metadata as embed_png_metadata, extract_metadata as extract_png_metadata
from ._svg import SVGMetadataError, embed_metadata as embed_svg_metadata, extract_metadata as extract_svg_metadata

_BASE_DIR = Path("figures")
_LATEST_DIR = _BASE_DIR / "latest"
_HISTORY_DIR = _BASE_DIR / "history"
_PNG_EXT = ".png"
_SVG_EXT = ".svg"
_SUPPORTED_EXTENSIONS = {_PNG_EXT, _SVG_EXT}


@dataclass(frozen=True)
class SaveResult:
    """Information about a saved figure."""

    latest_path: Path
    history_path: Path
    metadata: Mapping[str, Any]


def savefig(
    name: str,
    *,
    figure: Optional[Any] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    savefig_kwargs: Optional[Mapping[str, Any]] = None,
) -> SaveResult:
    """Save a matplotlib figure with embedded metadata."""
    path = Path(name)
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file extension '{suffix}'. Supported: {supported}")

    figure_obj = _resolve_figure(figure)
    metadata_payload = _build_metadata(path, metadata)
    image_format = suffix.lstrip(".")
    image_bytes = _render_figure(figure_obj, image_format, savefig_kwargs or {})
    try:
        if suffix == _PNG_EXT:
            image_bytes = embed_png_metadata(image_bytes, metadata_payload)
        else:
            image_bytes = embed_svg_metadata(image_bytes, metadata_payload)
    except (PNGMetadataError, SVGMetadataError) as exc:
        raise RuntimeError("Failed to embed metadata into figure output.") from exc

    latest_path = _LATEST_DIR / path.name
    history_path = _build_history_path(path, metadata_payload)

    _write_bytes(latest_path, image_bytes)
    _write_bytes(history_path, image_bytes)

    return SaveResult(latest_path=latest_path, history_path=history_path, metadata=metadata_payload)


def load_metadata(path: str | bytes | Path) -> Dict[str, Any]:
    """Load embedded metadata from an image file."""
    file_path = Path(path)
    data = file_path.read_bytes()
    try:
        if data.startswith(PNG_SIGNATURE):
            return extract_png_metadata(data)
        return extract_svg_metadata(data)
    except (PNGMetadataError, SVGMetadataError) as exc:
        raise RuntimeError(f"Unable to read refig metadata from {file_path}") from exc


def _resolve_figure(figure: Optional[Any]) -> Any:
    if figure is not None:
        return figure
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required to save figures with refig.") from exc
    current = plt.gcf()
    if current is None:
        raise RuntimeError("No active matplotlib figure is available to save.")
    return current


def _render_figure(figure: Any, image_format: str, savefig_kwargs: Mapping[str, Any]) -> bytes:
    buffer = io.BytesIO()
    kwargs = dict(savefig_kwargs)
    kwargs.setdefault("format", image_format)
    figure.savefig(buffer, **kwargs)
    return buffer.getvalue()


def _build_metadata(path: Path, extra: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc)
    metadata = {
        "figure": path.name,
        "created_at": timestamp.isoformat(),
        "source": _infer_source_path(),
        "cell_number": _infer_cell_number(),
        "git_commit": _infer_git_commit(),
        "refig_version": _get_refig_version(),
    }
    if extra:
        metadata.update(dict(extra))
    return metadata


def _build_history_path(path: Path, metadata: Mapping[str, Any]) -> Path:
    stem = path.stem
    figure_dir = _HISTORY_DIR / stem
    timestamp_token = _format_timestamp_token(metadata.get("created_at"))
    git_hash = _format_git_hash(metadata.get("git_commit"))
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        suffix = _PNG_EXT
    history_name = f"_{timestamp_token}_{git_hash}{suffix}"
    return figure_dir / history_name


def _format_timestamp_token(value: Any) -> str:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            sanitized = "".join(ch for ch in value if ch.isalnum())
            return sanitized or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    elif isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.strftime("%Y%m%dT%H%M%S")


def _format_git_hash(value: Any) -> str:
    if isinstance(value, str) and value:
        return (value.strip() or "nogit")[:7]
    return "nogit"


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _infer_source_path() -> Optional[str]:
    stack = traceback.extract_stack()
    for frame in reversed(stack[:-1]):
        filename = frame.filename
        if filename.startswith("<"):
            continue
        candidate = Path(filename)
        if _is_library_path(candidate):
            continue
        try:
            return str(candidate.resolve())
        except OSError:
            return filename
    return None


def _infer_cell_number() -> Optional[int]:
    try:
        from IPython import get_ipython  # type: ignore
    except Exception:
        return None
    shell = get_ipython()
    if hasattr(shell, "execution_count"):
        return getattr(shell, "execution_count")
    return None


def _infer_git_commit() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


@lru_cache(maxsize=1)
def _get_refig_version() -> Optional[str]:
    try:
        return importlib_metadata.version("refig")
    except importlib_metadata.PackageNotFoundError:
        return None


def _is_library_path(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(Path(__file__).resolve().parent)
    except Exception:
        return False
