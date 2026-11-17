"""Turn a run log into scorecard tables: by dimension, by data element, and the two together.

    uv run kit/scorecard.py files/day2/run_log_reference.csv
    uv run kit/scorecard.py out/run_log.csv --out out/scorecard.csv

It prints two headlines on purpose. "Rows passed" weights every row the same, so a large table
with an easy rule hides a small table with a broken one. "Rules meeting their threshold" counts
each rule once. A scorecard that shows only the first is the one this lab asks you to fix.
Rules that did not run (ERROR, NOT RUN) are listed, never dropped.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import LABS, show, utf8


def group(rows: list[dict], key: str) -> list[list]:
    out: dict[str, dict] = {}
    for r in rows:
        g = out.setdefault(r[key] or "?", {"rules": 0, "met": 0, "worst": None, "worst_rule": "", "failed": 0})
        g["rules"] += 1
        g["met"] += r["result"] == "PASS"
        g["failed"] += int(r["rows_failed"])
        rate = float(r["pass_rate"])
        if g["worst"] is None or rate < g["worst"]:
            g["worst"], g["worst_rule"] = rate, r["rule_id"]
    return [[k, v["rules"], v["met"], f"{v['worst']:.2f}", v["worst_rule"], v["failed"]]
            for k, v in sorted(out.items(), key=lambda kv: (kv[1]["met"] / kv[1]["rules"], kv[1]["worst"]))]


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("run_log")
    ap.add_argument("--out", default=str(LABS / "out" / "scorecard.csv"))
    a = ap.parse_args()
    with open(a.run_log, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    ran = [r for r in rows if r["result"] in ("PASS", "FAIL")]
    other = [r for r in rows if r["result"] not in ("PASS", "FAIL")]
    checked = sum(int(r["rows_checked"]) for r in ran)
    failed = sum(int(r["rows_failed"]) for r in ran)
    met = sum(r["result"] == "PASS" for r in ran)
    print(f"Headline A, rows passed: {100 * (checked - failed) / checked:.1f}% of {checked} rows checked")
    print(f"Headline B, rules meeting their threshold: {met} of {len(rows)} rules ({len(other)} did not run)")
    worst = min(ran, key=lambda r: float(r["pass_rate"]) - float(r["threshold"]))
    print(f"Furthest below its threshold: {worst['rule_id']} ({worst['cde']}) {worst['pass_rate']}% against {worst['threshold']}%\n")
    head = ["group", "rules", "met", "worst %", "worst rule", "rows failed"]
    print("By dimension (worst first)")
    by_dim = group(ran, "dimension")
    show(head, by_dim)
    print("\nBy data element (worst first)")
    by_cde = group(ran, "cde")
    show(head, by_cde)
    if other:
        print("\nDid not run")
        show(["rule", "result", "note"], [[r["rule_id"], r["result"], r.get("note", "")] for r in other])
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["view", *head])
        for r in by_dim:
            w.writerow(["dimension", *r])
        for r in by_cde:
            w.writerow(["element", *r])
        for r in other:
            w.writerow(["not run", r["rule_id"], "", "", "", r["result"], ""])
    print(f"\nscorecard tables: {out.name} (open in a spreadsheet; add thresholds, trend and the owner)")


if __name__ == "__main__":
    main()
