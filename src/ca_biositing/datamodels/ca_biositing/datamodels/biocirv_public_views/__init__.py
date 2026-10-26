"""BioCirV Public Dataset (`biocirv_public`) materialized views package.

This package provides SQLAlchemy `select()` expressions for the 5 materialized
views in the `biocirv_public` PostgreSQL schema supporting the BioCirV Living
Dataset (Stage 1 Zenodo release, `/v1/public` open API, and MCP server).

All views are governed by the centralized QC and privacy filter helpers in
`ca_biositing.datamodels.data_portal_views.common`:
- `get_resource_filter`
- `get_provider_filter`
- `get_qc_status_filter`
- `get_icp_filter`
- `get_sum_constraints_subquery`
"""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import String, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ColumnElement, FunctionElement

BIOCIRV_PUBLIC_SCHEMA = "biocirv_public"

# Explicit dependency order: mv_analytical_observations MUST be created/refreshed first.
BIOCIRV_PUBLIC_VIEW_NAMES: tuple[str, ...] = (
    "mv_analytical_observations",
    "mv_samples",
    "mv_resources",
    "mv_sample_summary",
    "mv_analytical_summary",
)


class ordered_string_agg(FunctionElement):
    """Dialect-aware `string_agg(col, separator ORDER BY col ASC)`.

    Compiles with `ORDER BY <col> ASC` on PostgreSQL for deterministic output
    across materialized view refreshes, and compiles as a plain 2-argument
    `string_agg(<col>, <sep>)` on SQLite (where `_SqliteStringAggAggregate`
    sorts deterministically in Python).
    """

    type = String()
    inherit_cache = True

    def __init__(self, col: ColumnElement[Any], separator: ColumnElement[Any]) -> None:
        super().__init__(col, separator)


@compiles(ordered_string_agg, "postgresql")
def _compile_ordered_string_agg_pg(
    element: ordered_string_agg, compiler: Any, **kw: Any
) -> str:
    clauses = list(element.clauses)
    col_sql = compiler.process(clauses[0], **kw)
    sep_sql = compiler.process(clauses[1], **kw)
    return f"string_agg({col_sql}, {sep_sql} ORDER BY {col_sql} ASC)"


@compiles(ordered_string_agg)
def _compile_ordered_string_agg_default(
    element: ordered_string_agg, compiler: Any, **kw: Any
) -> str:
    clauses = list(element.clauses)
    col_sql = compiler.process(clauses[0], **kw)
    sep_sql = compiler.process(clauses[1], **kw)
    return f"string_agg({col_sql}, {sep_sql})"


class _SqliteStddevAggregate:
    """Deterministic sample standard deviation (`STDDEV` / `STDDEV_SAMP`) for SQLite tests."""

    def __init__(self) -> None:
        self.values: list[float] = []

    def step(self, value: Any) -> None:
        if value is not None:
            try:
                self.values.append(float(value))
            except (TypeError, ValueError):
                pass

    def finalize(self) -> float | None:
        n = len(self.values)
        if n < 2:
            return None
        mean = sum(self.values) / n
        variance = sum((x - mean) ** 2 for x in self.values) / (n - 1)
        return math.sqrt(variance)


class _SqliteStringAggAggregate:
    """Deterministic 2-argument `string_agg(value, separator)` for SQLite tests."""

    def __init__(self) -> None:
        self.values: list[str] = []
        self.separator: str = "; "

    def step(self, value: Any, separator: Any = "; ") -> None:
        if separator is not None:
            self.separator = str(separator)
        if value is not None:
            text_val = str(value)
            if text_val not in self.values:
                self.values.append(text_val)

    def finalize(self) -> str | None:
        if not self.values:
            return None
        return self.separator.join(sorted(self.values))


def _register_sqlite_connection_udfs(dbapi_connection: Any) -> None:
    """Register `stddev` and `string_agg` aggregates on a raw SQLite DBAPI connection."""
    create_aggregate = getattr(dbapi_connection, "create_aggregate", None)
    if callable(create_aggregate):
        create_aggregate("stddev", 1, _SqliteStddevAggregate)
        create_aggregate("string_agg", 2, _SqliteStringAggAggregate)


def register_sqlite_udfs(engine_or_conn: Any) -> None:
    """Ensure SQLite connections support `stddev` and `string_agg` aggregates.

    Can be passed a SQLAlchemy `Engine`, `Connection`, or `Session`.
    """
    engine: Engine | None = None
    if isinstance(engine_or_conn, Engine):
        engine = engine_or_conn
    elif hasattr(engine_or_conn, "engine") and isinstance(engine_or_conn.engine, Engine):
        engine = engine_or_conn.engine
    elif hasattr(engine_or_conn, "get_bind"):
        bind = engine_or_conn.get_bind()
        if isinstance(bind, Engine):
            engine = bind
        elif hasattr(bind, "engine") and isinstance(bind.engine, Engine):
            engine = bind.engine

    if engine is not None and engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _on_connect(dbapi_conn: Any, _connection_record: Any) -> None:
            _register_sqlite_connection_udfs(dbapi_conn)

    # Also register on an already-open raw connection if present
    raw_conn = getattr(engine_or_conn, "connection", None)
    if callable(raw_conn):
        try:
            conn_obj = raw_conn()
            driver_conn = getattr(conn_obj, "driver_connection", None) or getattr(
                conn_obj, "connection", None
            )
            if driver_conn is not None:
                _register_sqlite_connection_udfs(driver_conn)
        except Exception:
            pass


from .mv_analytical_observations import mv_analytical_observations  # noqa: E402
from .mv_analytical_summary import mv_analytical_summary  # noqa: E402
from .mv_resources import mv_resources  # noqa: E402
from .mv_sample_summary import mv_sample_summary  # noqa: E402
from .mv_samples import mv_samples  # noqa: E402

__all__ = [
    "BIOCIRV_PUBLIC_SCHEMA",
    "BIOCIRV_PUBLIC_VIEW_NAMES",
    "mv_analytical_observations",
    "mv_analytical_summary",
    "mv_resources",
    "mv_sample_summary",
    "mv_samples",
    "ordered_string_agg",
    "register_sqlite_udfs",
]
