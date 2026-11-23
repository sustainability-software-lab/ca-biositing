"""Local-first and GCS-backed dashboard asset loader with TTL + ETag caching."""

from __future__ import annotations

from dataclasses import dataclass
import mimetypes
import os
from pathlib import Path
import time
from typing import Any

from urllib.parse import quote

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
  <script src="https://accounts.google.com/gsi/client" async defer></script>
</head>
<body>
  <main style="max-width: 480px; margin: 4rem auto; font-family: sans-serif;">
    <h1>BioCirV Analytics &amp; QC Audit Portal</h1>
    <p>Sign in with an authorized Google account (<code>@lbl.gov</code>, <code>@ucdavis.edu</code>, or <code>@beamcircular.org</code>) to access the BioCirV dashboards.</p>
    <div id="portal-auth-root" data-auth-endpoint="/v1/qc/auth/google" data-dev-login-endpoint="/v1/qc/auth/dev-login"></div>
    <div id="google-gsi-button" style="margin: 1.5rem 0;"></div>
    <div id="login-msg" style="margin-top: 1rem; color: #0284c7;"></div>
  </main>
  <script>
    (function () {
      function getNextUrl() {
        var params = new URLSearchParams(window.location.search);
        var next = params.get("next");
        if (next && next.startsWith("/") && !next.startsWith("//")) return next;
        return "/v1/dashboards/index.html";
      }
      function onGoogleCredential(resp) {
        fetch("/v1/qc/auth/google", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ credential: resp.credential, id_token: resp.credential })
        })
          .then(function (r) { return r.json(); })
          .then(function (res) {
            if (res && res.authenticated) {
              window.location.replace(getNextUrl());
            } else {
              document.getElementById("login-msg").textContent = (res && res.detail) || "Login failed.";
            }
          });
      }
      fetch("/v1/qc/auth/config", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (cfg) {
          if (!cfg || !cfg.google_client_id) return;
          var tries = 0;
          var timer = setInterval(function () {
            tries++;
            if (window.google && window.google.accounts && window.google.accounts.id) {
              clearInterval(timer);
              window.google.accounts.id.initialize({
                client_id: cfg.google_client_id,
                callback: onGoogleCredential
              });
              window.google.accounts.id.renderButton(
                document.getElementById("google-gsi-button"),
                { theme: "outline", size: "large", text: "signin_with", shape: "rectangular" }
              );
            } else if (tries > 40) {
              clearInterval(timer);
            }
          }, 150);
        });
    })();
  </script>
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


class _RestBlob:
    """Lightweight GCS blob adapter using `google.auth.transport.requests.AuthorizedSession`."""

    def __init__(self, session: Any, bucket_name: str, blob_name: str) -> None:
        self._session = session
        self.bucket_name = bucket_name
        self.name = blob_name
        self.etag: str | None = None
        self._metadata_loaded = False
        self._exists: bool | None = None

    def _meta_url(self) -> str:
        encoded = quote(self.name, safe="")
        return f"https://storage.googleapis.com/storage/v1/b/{self.bucket_name}/o/{encoded}"

    def reload(self) -> None:
        resp = self._session.get(self._meta_url(), timeout=10)
        self._metadata_loaded = True
        if resp.status_code == 200:
            self._exists = True
            data = resp.json()
            self.etag = data.get("etag")
        elif resp.status_code == 404:
            self._exists = False
        else:
            resp.raise_for_status()

    def exists(self) -> bool:
        if not self._metadata_loaded:
            try:
                self.reload()
            except Exception:
                return False
        return bool(self._exists)

    def download_as_bytes(self) -> bytes:
        resp = self._session.get(
            f"{self._meta_url()}?alt=media",
            timeout=30,
        )
        resp.raise_for_status()
        if not self.etag:
            self.etag = resp.headers.get("ETag")
        return resp.content


class _RestBucket:
    """Lightweight GCS bucket adapter for `_AuthorizedRestGcsClient`."""

    def __init__(self, session: Any, name: str) -> None:
        self._session = session
        self.name = name

    def blob(self, blob_name: str) -> _RestBlob:
        return _RestBlob(self._session, self.name, blob_name)


class _AuthorizedRestGcsClient:
    """ADC-backed GCS client using `google-auth` (installed in the `webservice` Pixi env)."""

    def __init__(self) -> None:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/devstorage.read_only"]
        )
        self._session = AuthorizedSession(credentials)

    def bucket(self, bucket_name: str) -> _RestBucket:
        return _RestBucket(self._session, bucket_name)


def get_gcs_storage_client() -> Any:
    """Instantiate a Google Cloud Storage client lazily, falling back to `google-auth` REST."""
    try:
        from google.cloud import storage  # type: ignore[import-untyped]

        return storage.Client()
    except ImportError:
        return _AuthorizedRestGcsClient()


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

    try:
        client = gcs_client if gcs_client is not None else get_gcs_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
    except Exception:
        return None

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
