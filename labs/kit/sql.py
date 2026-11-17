"""Run one SQL query, or a file of queries, on the case tables.

    uv run kit/sql.py "SELECT city_code, count(*) FROM centres GROUP BY 1"
    uv run kit/sql.py -f my_queries.sql          # every statement in the file, one after another
    uv run kit/sql.py --data <folder> "..."      # the same tables from another folder

Tables: applications, centres, licences, inspections, and the code lists cities, districts,
codes_outcome. Any CSV file can be read too: SELECT * FROM 'files/day1/report_2026_10.csv'.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import connect, query, show, utf8


def statements(text: str) -> list[str]:
    lines = [l for l in text.splitlines() if not l.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="?")
    ap.add_argument("-f", "--file")
    ap.add_argument("--data")
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()
    con = connect(a.data)
    todo = statements(Path(a.file).read_text(encoding="utf-8")) if a.file else [a.sql]
    for i, s in enumerate(todo, 1):
        if len(todo) > 1:
            print(f"\n-- [{i}] {s.splitlines()[0][:90]}")
        try:
            h, rows = query(con, s)
        except Exception as e:  # show the engine message, not a traceback
            print("error: " + str(e).strip().splitlines()[0])
            continue
        show(h, rows, a.limit)


if __name__ == "__main__":
    main()
