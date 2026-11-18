"""Pre-release checks on an extract before it is shared or published.

    uv run kit/prerelease.py files/day3/open_data_extract.csv

Six checks: home addresses (a home nursery's building number and postal code locate a family's
home), small groups (fewer than three home nurseries in a district), expired licences listed as
current, repeated centres, impossible places, and a city that its postal code contradicts. A
passing set of rules on the source does not make an extract safe to publish: this is its own gate.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import REPORT_DATE, connect, csv_view, show, utf8

CHECKS = [
    ("P1", "عنوان منزل في صف حضانة منزلية", "centre_kind = 'حضانة منزلية' AND (building_no IS NOT NULL OR postal_code IS NOT NULL)"),
    ("P2", "رخصة منتهية تظهر سارية", f"CAST(licence_expiry AS DATE) < DATE '{REPORT_DATE}'"),
    ("P3", "مركز مكرر", "centre_id IN (SELECT centre_id FROM x GROUP BY 1 HAVING count(*) > 1)"),
    ("P4", "مقاعد غير معقولة", "licensed_places > 150 OR licensed_places < 1"),
    ("P5", "حي فيه أقل من ثلاث حضانات منزلية", "centre_kind = 'حضانة منزلية' AND district_code IN (SELECT district_code FROM x WHERE centre_kind = 'حضانة منزلية' GROUP BY 1 HAVING count(*) < 3)"),
    ("P6", "المدينة لا يطابقها الرمز البريدي", "length(CAST(postal_code AS VARCHAR)) = 6 AND substr(CAST(postal_code AS VARCHAR), 1, 2) <> (SELECT postal_prefix FROM cities WHERE city_name = x.city)"),
]


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("extract")
    a = ap.parse_args()
    con = connect()
    con.execute(f"CREATE VIEW x AS SELECT * FROM read_csv('{Path(a.extract).as_posix()}', header=true, all_varchar=false, types={{'postal_code': 'VARCHAR', 'building_no': 'VARCHAR', 'district_code': 'VARCHAR'}})")
    total = con.execute("SELECT count(*) FROM x").fetchone()[0]
    rows = []
    for cid, label, cond in CHECKS:
        n = con.execute(f"SELECT count(*) FROM x WHERE {cond}").fetchone()[0]
        rows.append([cid, label, n, "PASS" if n == 0 else "FAIL"])
    print(f"extract: {total} rows")
    show(["check", "what", "rows", "result"], rows)
    bad = sum(r[3] == "FAIL" for r in rows)
    print("\nverdict: " + ("no check failed; the owner still signs the release" if not bad else f"{bad} checks failed: do not publish as it is"))


if __name__ == "__main__":
    main()
