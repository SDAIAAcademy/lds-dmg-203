"""Shared helpers of the lab kit: the case tables as DuckDB views, and plain-text tables."""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

LABS = Path(__file__).resolve().parents[1]
FILES = LABS / "files"
DATA = FILES / "data"
REPORT_DATE = "2026-10-31"

# Every code-like column is read as text: a postal code that starts with zero must stay as written.
TYPES = {
    "centres": {"centre_id": "VARCHAR", "centre_type": "VARCHAR", "city_code": "VARCHAR", "district_code": "VARCHAR",
                "building_no": "VARCHAR", "postal_code": "VARCHAR", "owner_id": "VARCHAR", "opened_date": "DATE"},
    "applications": {"application_id": "VARCHAR", "centre_id": "VARCHAR", "app_type": "VARCHAR", "channel": "VARCHAR",
                     "form_version": "VARCHAR", "premises_same_as_owner": "VARCHAR", "submitted_at": "DATE",
                     "decision": "VARCHAR", "decision_date": "DATE", "capacity_requested": "INTEGER"},
    "licences": {"licence_no": "VARCHAR", "application_id": "VARCHAR", "centre_id": "VARCHAR", "issue_date": "DATE",
                 "expiry_date": "DATE", "status": "VARCHAR", "capacity_licensed": "INTEGER"},
    "inspections": {"inspection_id": "VARCHAR", "licence_no": "VARCHAR", "inspection_date": "DATE", "entered_at": "DATE",
                    "inspector_id": "VARCHAR", "office_city": "VARCHAR", "reassigned": "VARCHAR", "outcome": "VARCHAR",
                    "score": "INTEGER", "followup_scheduled": "VARCHAR"},
    "cities": {"city_code": "VARCHAR", "city_name": "VARCHAR", "postal_prefix": "VARCHAR", "inspection_office": "VARCHAR"},
    "districts": {"district_code": "VARCHAR", "city_code": "VARCHAR", "district_name": "VARCHAR", "postal_digits": "VARCHAR"},
    "codes_outcome": {"code": "VARCHAR", "meaning": "VARCHAR"},
}
KEYS = {"centres": "centre_id", "applications": "application_id", "licences": "licence_no", "inspections": "inspection_id"}


def utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")


def sql_path(p: Path) -> str:
    return str(p).replace("\\", "/").replace("'", "''")


def connect(data: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """An in-memory database with one view per case table, read from data/ (or another folder)."""
    folder = Path(data) if data else DATA
    con = duckdb.connect()
    for name, cols in TYPES.items():
        f = folder / f"{name}.csv"
        if not f.exists():
            f = DATA / f"{name}.csv"
        spec = ", ".join(f"'{k}': '{v}'" for k, v in cols.items())
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_csv('{sql_path(f)}', header=true, columns={{{spec}}}, nullstr='')")
    return con


def csv_view(con: duckdb.DuckDBPyConnection, name: str, path: Path, all_text: bool = False) -> None:
    extra = ", all_varchar=true" if all_text else ""
    con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv_auto('{sql_path(path)}', header=true{extra})")


def show(headers: list[str], rows: list, limit: int = 50) -> None:
    """Print rows as an aligned plain-text table."""
    rows = [["" if v is None else str(v) for v in r] for r in rows]
    shown = rows[:limit]
    widths = [max([len(h)] + [len(r[i]) for r in shown]) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  ".join("-" * w for w in widths))
    for r in shown:
        print("  ".join(v.ljust(w) for v, w in zip(r, widths)))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more rows")
    print(f"({len(rows)} rows)")


def query(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list]:
    cur = con.execute(sql)
    return [d[0] for d in cur.description], cur.fetchall()
