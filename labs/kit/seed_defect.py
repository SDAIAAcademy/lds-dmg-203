"""For the assessor: copy the case tables and plant one new defect, chosen at the defence.

    uv run kit/seed_defect.py --kind codes --out out/seeded --seed 7
    uv run kit/run_checks.py <participant's checks> --data out/seeded

Kinds: nulls (empty inspection outcomes), duplicates (licence rows repeated), codes (a status
spelled another way), orphans (inspections of licences that do not exist), range (impossible
places), stale (current status on an expired licence), postal (postal codes cut short).
The assessor picks the kind and the seed during the defence and says nothing in advance; the
participant runs the same checks on the copy and shows which rule caught it, or why none did.
"""
from __future__ import annotations

import argparse
import csv
import random
import shutil
from pathlib import Path

from common import DATA, REPORT_DATE, utf8

KINDS = {
    "nulls": ("inspections", "outcome"),
    "duplicates": ("licences", None),
    "codes": ("licences", "status"),
    "orphans": ("inspections", "licence_no"),
    "range": ("licences", "capacity_licensed"),
    "stale": ("licences", "status"),
    "postal": ("centres", "postal_code"),
}


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=sorted(KINDS), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--rows", type=int, default=25)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DATA, out)
    table, col = KINDS[a.kind]
    path = out / f"{table}.csv"
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())
    if a.kind == "nulls":
        for r in rng.sample(rows, a.rows):
            r[col] = ""
    elif a.kind == "duplicates":
        rows.extend(dict(r) for r in rng.sample(rows, a.rows))
    elif a.kind == "codes":
        for r in rng.sample([r for r in rows if r["status"] == "ACTIVE"], a.rows):
            r[col] = "Active"
    elif a.kind == "orphans":
        for r in rng.sample(rows, a.rows):
            r[col] = r[col].replace("AKM-L-", "AKM-X-")
    elif a.kind == "range":
        for r in rng.sample(rows, a.rows):
            r[col] = str(-rng.randint(1, 30))
    elif a.kind == "stale":
        for r in rng.sample([r for r in rows if r["status"] == "EXPIRED" and r["expiry_date"] < REPORT_DATE], a.rows):
            r[col] = "ACTIVE"
    elif a.kind == "postal":
        for r in rng.sample(rows, a.rows):
            r[col] = r[col][:4]
    rng.shuffle(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"seeded {a.kind}: {a.rows} rows in {table}{'.' + col if col else ''}; copy in {out}")


if __name__ == "__main__":
    main()
