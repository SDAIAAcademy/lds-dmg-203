"""Check the SQL pre-work: run your answers and the reference answers, and compare the values.

    uv run kit/check_prework.py files/prework/sql_drills.sql
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import LABS, connect, utf8
from sql import statements


def norm(rows: list) -> list:
    out = []
    for r in rows:
        out.append(tuple(round(v, 1) if isinstance(v, float) else str(v) if v is not None else "" for v in r))
    return sorted(out)


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("answers")
    a = ap.parse_args()
    con = connect()
    mine = statements(Path(a.answers).read_text(encoding="utf-8"))
    ref = statements((LABS / "solutions" / "prework_answers.sql").read_text(encoding="utf-8"))
    ok = 0
    for i, r in enumerate(ref, 1):
        if i > len(mine):
            print(f"Q{i}: missing")
            continue
        try:
            got = norm(con.execute(mine[i - 1]).fetchall())
        except Exception as e:
            print(f"Q{i}: error: {str(e).splitlines()[0][:120]}")
            continue
        want = norm(con.execute(r).fetchall())
        if got == want:
            ok += 1
            print(f"Q{i}: correct")
        else:
            print(f"Q{i}: different ({len(got)} rows, expected {len(want)}); first row you got: {got[:1]}")
    print(f"\n{ok} of {len(ref)} correct")


if __name__ == "__main__":
    main()
