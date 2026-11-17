"""The course's declarative check engine: rules written in a YAML file, run as SQL on DuckDB.

    uv run kit/run_checks.py files/day2/checks_start.yml
    uv run kit/run_checks.py my_checks.yml --catalogue files/day2/rules_reference.csv --out out/run_log.csv
    uv run kit/run_checks.py my_checks.yml --data <another data folder>

A check states what must hold; the engine writes the SQL. Types:
  not_null   column must have a value (empty text counts as missing)
  in_set     column must be one of values
  pattern    column must match a regular expression (whole value)
  between    column must lie between min and max
  unique     the combination of columns must not repeat
  reference  column must exist in ref_table.ref_column
  row        any SQL condition that each row must satisfy (must:), over table or a from: clause
Every check may add where: (the scope). Empty values are not checked by in_set, pattern, between
and reference: completeness is its own rule. The run log has one line per rule, failed or not,
and lists sample keys of failing rows, never other values: a check may touch personal data.
With --catalogue, rules of the catalogue that have no check are listed as NOT RUN.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml

from common import KEYS, LABS, REPORT_DATE, connect, show, utf8

FIELDS = ["run_date", "rule_id", "cde", "dimension", "table", "rows_checked", "rows_failed", "pass_rate",
          "threshold", "result", "owner", "sample_keys", "note"]


def build(c: dict) -> tuple[str, str, str]:
    """Return (from-clause, scope condition, failure condition) for one check."""
    t = c["table"]
    src = c.get("from", t)
    scope = c.get("where", "TRUE")
    kind = c["type"]
    col = c.get("column")
    has = f"({col} IS NOT NULL AND trim(CAST({col} AS VARCHAR)) <> '')" if col else "TRUE"
    if kind == "not_null":
        return src, scope, f"NOT {has}"
    if kind == "in_set":
        vals = ", ".join("'" + str(v).replace("'", "''") + "'" for v in c["values"])
        return src, f"({scope}) AND {has}", f"CAST({col} AS VARCHAR) NOT IN ({vals})"
    if kind == "pattern":
        pat = c["pattern"].replace("'", "''")
        return src, f"({scope}) AND {has}", f"NOT regexp_full_match(CAST({col} AS VARCHAR), '{pat}')"
    if kind == "between":
        return src, f"({scope}) AND {col} IS NOT NULL", f"NOT ({col} BETWEEN {c['min']} AND {c['max']})"
    if kind == "reference":
        ref = f"SELECT {c['ref_column']} FROM {c['ref_table']}"
        return src, f"({scope}) AND {has}", f"{col} NOT IN ({ref})"
    if kind == "row":
        return src, scope, f"NOT coalesce(({c['must']}), FALSE)"
    raise ValueError(f"unknown type {kind}")


def run_one(con, c: dict) -> dict:
    t = c["table"]
    key = c.get("key", KEYS.get(t, "rowid"))
    out = {"rule_id": c["id"], "cde": c.get("cde", ""), "dimension": c.get("dimension", ""), "table": t,
           "threshold": c.get("threshold", 100), "owner": c.get("owner", ""), "note": ""}
    if c["type"] == "unique":
        cols = ", ".join(c["columns"])
        scope = c.get("where", "TRUE")
        src = c.get("from", t)
        checked = con.execute(f"SELECT count(*) FROM {src} WHERE {scope}").fetchone()[0]
        failed = con.execute(f"SELECT coalesce(sum(n - 1), 0) FROM (SELECT count(*) n FROM {src} WHERE {scope} GROUP BY {cols} HAVING count(*) > 1)").fetchone()[0]
        sample = [r[0] for r in con.execute(f"SELECT {key} FROM {src} WHERE {scope} AND ({cols}) IN (SELECT ({cols}) FROM {src} WHERE {scope} GROUP BY {cols} HAVING count(*) > 1) ORDER BY 1 LIMIT 5").fetchall()]
    else:
        src, scope, fail = build(c)
        checked = con.execute(f"SELECT count(*) FROM {src} WHERE {scope}").fetchone()[0]
        failed = con.execute(f"SELECT count(*) FROM {src} WHERE ({scope}) AND ({fail})").fetchone()[0]
        sample = [r[0] for r in con.execute(f"SELECT {key} FROM {src} WHERE ({scope}) AND ({fail}) ORDER BY 1 LIMIT 5").fetchall()]
    rate = 100.0 * (checked - failed) / checked if checked else 100.0
    out.update({"rows_checked": checked, "rows_failed": int(failed), "pass_rate": f"{rate:.2f}",
                "result": "PASS" if rate >= float(out["threshold"]) else "FAIL", "sample_keys": " ".join(map(str, sample))})
    if not checked:
        out["note"] = "no rows in scope"
    return out


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("checks")
    ap.add_argument("--data")
    ap.add_argument("--catalogue")
    ap.add_argument("--out", default=str(LABS / "out" / "run_log.csv"))
    a = ap.parse_args()
    spec = yaml.safe_load(Path(a.checks).read_text(encoding="utf-8"))
    con = connect(a.data)
    log = []
    for c in spec["checks"]:
        try:
            r = run_one(con, c)
        except Exception as e:  # a broken rule is logged, not skipped
            r = {"rule_id": c.get("id", "?"), "cde": c.get("cde", ""), "dimension": c.get("dimension", ""),
                 "table": c.get("table", ""), "rows_checked": "", "rows_failed": "", "pass_rate": "",
                 "threshold": c.get("threshold", ""), "result": "ERROR", "owner": c.get("owner", ""),
                 "sample_keys": "", "note": str(e).splitlines()[0][:160]}
        r["run_date"] = spec.get("run_date", REPORT_DATE)
        log.append(r)
    if a.catalogue:
        with open(a.catalogue, encoding="utf-8") as f:
            ids = [row["rule_id"] for row in csv.DictReader(f)]
        have = {r["rule_id"] for r in log}
        for rid in ids:
            if rid not in have:
                log.append({"run_date": spec.get("run_date", REPORT_DATE), "rule_id": rid, "result": "NOT RUN",
                            "note": "in the catalogue, no check written"})
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, FIELDS, lineterminator="\n")
        w.writeheader()
        for r in log:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    show(["rule", "dimension", "checked", "failed", "pass %", "threshold", "result"],
         [[r["rule_id"], r.get("dimension", ""), r.get("rows_checked", ""), r.get("rows_failed", ""),
           r.get("pass_rate", ""), r.get("threshold", ""), r["result"]] for r in log], 100)
    counts = {k: sum(1 for r in log if r["result"] == k) for k in ("PASS", "FAIL", "ERROR", "NOT RUN")}
    print("summary: " + "  ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"run log: {out.relative_to(LABS) if out.is_relative_to(LABS) else out}")


if __name__ == "__main__":
    main()
