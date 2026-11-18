"""Profile the columns of one case table (or any CSV file): what a first look at the data shows.

    uv run kit/profile.py centres
    uv run kit/profile.py files/examples/permits.csv

For each column: rows, empty values, distinct values, smallest and largest, the five most common
values, and the three most common shapes (9 = a digit, A = a Latin letter, ع = an Arabic letter).
A profile shows what is there. Whether it is a defect is your judgement against the rules.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from common import KEYS, connect, csv_view, query, utf8


def shape(v: str) -> str:
    s = re.sub(r"[0-9]", "9", v)
    s = re.sub(r"[A-Za-z]", "A", s)
    s = re.sub(r"[؀-ۿ]", "ع", s)
    s = re.sub(r"ع+", "ع…", s)
    return s if len(s) <= 24 else s[:24] + "…"


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("--data")
    a = ap.parse_args()
    con = connect(a.data)
    name = a.table
    if name not in KEYS and name not in ("cities", "districts", "codes_outcome"):
        csv_view(con, "t", Path(a.table), all_text=False)
        name = "t"
    cols = [r[0] for r in con.execute(f"DESCRIBE {name}").fetchall()]
    types = {r[0]: r[1] for r in con.execute(f"DESCRIBE {name}").fetchall()}
    total = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
    print(f"table {a.table}: {total} rows, {len(cols)} columns\n")
    for c in cols:
        q = f'"{c}"'
        nulls = con.execute(f"SELECT count(*) FROM {name} WHERE {q} IS NULL").fetchone()[0]
        blank = con.execute(f"SELECT count(*) FROM {name} WHERE {q} IS NOT NULL AND trim(CAST({q} AS VARCHAR)) = ''").fetchone()[0]
        distinct = con.execute(f"SELECT count(DISTINCT {q}) FROM {name}").fetchone()[0]
        lo, hi = con.execute(f"SELECT min({q}), max({q}) FROM {name}").fetchone()
        _, top = query(con, f"SELECT CAST({q} AS VARCHAR) v, count(*) n FROM {name} GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 5")
        vals = [r[0] for r in con.execute(f"SELECT CAST({q} AS VARCHAR) FROM {name} WHERE {q} IS NOT NULL").fetchall()]
        shapes = Counter(shape(v) for v in vals).most_common(3)
        print(f"■ {c}  ({types[c]})")
        print(f"   empty: {nulls + blank}   distinct: {distinct}   min: {lo}   max: {hi}")
        print("   most common: " + " | ".join(f"{v if v is not None else '∅'} ×{n}" for v, n in top))
        print("   shapes: " + " | ".join(f"{s} ×{n}" for s, n in shapes))
    print("\nNext: write the query that shows each suspicion, and log it with its row count.")


if __name__ == "__main__":
    main()
