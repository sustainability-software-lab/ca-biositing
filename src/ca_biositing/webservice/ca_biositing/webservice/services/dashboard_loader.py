"""Local-first and GCS-backed dashboard asset loader with TTL + ETag caching."""

from __future__ import annotations

from dataclasses import dataclass
import mimetypes
import os
from pathlib import Path
import time
from typing import Any

from fastapi import HTTPException, status

from ca_biositing.webservice.config import config

DEFAULT_EXPORTS_PLOTS_DIR = (
    Path(__file__).resolve().parents[6] / "exports" / "plots"
)

BUILTIN_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BioCirV Portal Login</title>
</head>
<body>
  <main style="max-width: 480px; margin: 4rem auto; font-family: sans-serif;">
    <h1>BioCirV Analytics &amp; QC Audit Portal</h1>
    <p>Sign in with an authorized Google account (<code>@lbl.gov</code>, <code>@ucdavis.edu</code>, or <code>@beamcircular.org</code>) to access the BioCirV dashboards.</p>
    <div id="portal-auth-root" data-auth-endpoint="/v1/qc/auth/google" data-dev-login-endpoint="/v1/qc/auth/dev-login"></div>
  </main>
</body>
</html>
"""


@dataclass
class _CachedAsset:
    content: bytes
    media_type: str
    etag: str | None
    fetched_at: float


_GCS_ASSET_CACHE: dict[tuple[str, str], _CachedAsset] = {}


def clear_dashboard_cache() -> None:
    """Clear the in-memory GCS dashboard asset cache."""
    _GCS_ASSET_CACHE.clear()


def get_exports_plots_dir() -> Path:
    """Return the local dashboard exports directory (supports test override)."""
    override = os.environ.get("BIOSITING_DASHBOARDS_LOCAL_DIR", "").strip()
    if override:
        return Path(override)
    return DEFAULT_EXPORTS_PLOTS_DIR


def sanitize_dashboard_subpath(subpath: str) -> str:
    """Validate and normalize a dashboard relative subpath, rejecting traversal attempts."""
    raw = (subpath or "").strip()
    if "\x00" in raw or "\\" in raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard path.",
        )

    if not raw or raw == "/":
        return "index.html"

    if raw.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard path: leading slash not allowed.",
        )

    has_trailing_slash = raw.endswith("/")
    parts = [part for part in raw.split("/") if part]
    if not parts:
        return "index.html"

    for part in parts:
        if part in {".", ".."}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid dashboard path: traversal segments are not allowed.",
            )

    normalized = "/".join(parts)
    if has_trailing_slash:
        normalized = f"{normalized}/index.html"
    return normalized


def guess_media_type(subpath: str) -> str:
    """Guess the HTTP Content-Type for a dashboard asset."""
    guessed, _ = mimetypes.guess_type(subpath)
    if guessed:
        if guessed.startswith("text/") or guessed in {
            "application/javascript",
            "application/json",
        }:
            return f"{guessed}; charset=utf-8"
        return guessed
    if subpath.endswith(".html"):
        return "text/html; charset=utf-8"
    return "application/octet-stream"


def get_gcs_storage_client() -> Any:
    """Instantiate a Google Cloud Storage client lazily."""
    from google.cloud import storage  # type: ignore[import-untyped]

    return storage.Client()


def _fetch_from_gcs(
    bucket_name: str,
    prefix: str,
    clean_subpath: str,
    gcs_client: Any = None,
    ttl_seconds: int = 60,
) -> tuple[bytes, str, str] | None:
    """Fetch a dashboard asset from GCS with in-memory TTL and ETag caching."""
    clean_prefix = (prefix or "").strip("/")
    blob_name = f"{clean_prefix}/{clean_subpath}" if clean_prefix else clean_subpath
    cache_key = (bucket_name, blob_name)
    now = time.monotonic()

    cached = _GCS_ASSET_CACHE.get(cache_key)
    if cached is not None and (now - cached.fetched_at) < ttl_seconds:
        return cached.content, cached.media_type, "gcs_cache"

    client = gcs_client if gcs_client is not None else get_gcs_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    exists_fn = getattr(blob, "exists", None)
    if callable(exists_fn) and not exists_fn():
        _GCS_ASSET_CACHE.pop(cache_key, None)
        return None

    reload_fn = getattr(blob, "reload", None)
    if cached is not None and callable(reload_fn):
        try:
            reload_fn()
            current_etag = getattr(blob, "etag", None)
            if current_etag and cached.etag and current_etag == cached.etag:
                cached.fetched_at = now
                return cached.content, cached.media_type, "gcs_cache"
        except Exception:
            pass

    try:
        content = blob.download_as_bytes()
    except Exception:
        return None

    media_type = guess_media_type(clean_subpath)
    etag = getattr(blob, "etag", None)
    _GCS_ASSET_CACHE[cache_key] = _CachedAsset(
        content=content,
        media_type=media_type,
        etag=etag,
        fetched_at=now,
    )
    return content, media_type, "gcs"


def load_dashboard_asset(
    subpath: str,
    gcs_client: Any = None,
    local_dir: Path | None = None,
    ttl_seconds: int = 60,
) -> tuple[bytes, str, str]:
    """Load a dashboard asset from local `exports/plots` first, then GCS fallback.

    Returns:
        Tuple of `(content_bytes, media_type, source)`.
    """
    clean_subpath = sanitize_dashboard_subpath(subpath)
    base_dir = (local_dir or get_exports_plots_dir()).resolve()
    candidate_path = (base_dir / clean_subpath).resolve()

    if not candidate_path.is_relative_to(base_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard path outside root directory.",
        )

    if candidate_path.is_dir():
        index_candidate = (candidate_path / "index.html").resolve()
        if index_candidate.is_relative_to(base_dir) and index_candidate.is_file():
            return (
                index_candidate.read_bytes(),
                guess_media_type("index.html"),
                "local",
            )
    elif candidate_path.is_file():
        return (
            candidate_path.read_bytes(),
            guess_media_type(clean_subpath),
            "local",
        )

    bucket_name = (config.dashboards_bucket_name or "").strip()
    if bucket_name or gcs_client is not None:
        effective_bucket = bucket_name or "biocirv-dashboards"
        gcs_result = _fetch_from_gcs(
            bucket_name=effective_bucket,
            prefix=config.dashboards_gcs_prefix,
            clean_subpath=clean_subpath,
            gcs_client=gcs_client,
            ttl_seconds=ttl_seconds,
        )
        if gcs_result is not None:
            return gcs_result

    if clean_subpath == "login.html":
        return (
            BUILTIN_LOGIN_HTML.encode("utf-8"),
            "text/html; charset=utf-8",
            "builtin_fallback",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Dashboard asset '{clean_subpath}' not found.",
    )
