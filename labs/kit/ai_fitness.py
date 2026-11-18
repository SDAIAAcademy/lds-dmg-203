"""Measure whether two datasets are fit for an AI use.

    uv run kit/ai_fitness.py table   # inspection history for training an inspection-risk model
    uv run kit/ai_fitness.py docs    # requirement documents for grounding an applicant assistant

The measures are the evidence; the call (use, fix or reject) and its reasons are yours.
table: subgroup coverage against the licensed population, exact duplicates, the agreement of two
inspectors on the same visits (label noise), a column that is only known after the outcome
(leakage), and the share of rows from the checklist that is no longer used (currency).
docs: near duplicates, superseded versions still in the collection, numbers that disagree on the
same topic, documents without an effective date or not reviewed within a year, and documents
that hold personal data.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from common import FILES, REPORT_DATE, connect, csv_view, query, show, utf8

AI = FILES / "day3" / "ai"


def table() -> None:
    con = connect()
    csv_view(con, "h", AI / "inspection_history.csv")
    csv_view(con, "pop", AI / "licensed_population.csv")
    csv_view(con, "audit", AI / "label_audit.csv")
    n = con.execute("SELECT count(*) FROM h").fetchone()[0]
    print(f"rows: {n}\n\n1. Coverage by city and type: share of training rows against share of licensed centres")
    h, rows = query(con, """
        WITH t AS (SELECT city_code, centre_type, count(*) n FROM h GROUP BY ALL),
             p AS (SELECT city_code, centre_type, centres FROM pop)
        SELECT p.city_code, p.centre_type, coalesce(t.n, 0) AS rows,
               round(100.0 * coalesce(t.n, 0) / sum(coalesce(t.n, 0)) OVER (), 1) AS train_pct,
               round(100.0 * p.centres / sum(p.centres) OVER (), 1) AS population_pct,
               round((100.0 * coalesce(t.n, 0) / sum(coalesce(t.n, 0)) OVER ()) / (100.0 * p.centres / sum(p.centres) OVER ()), 2) AS ratio
        FROM p LEFT JOIN t USING (city_code, centre_type) ORDER BY ratio""")
    show(h, rows)
    dup = con.execute("""SELECT coalesce(sum(k - 1), 0) FROM (SELECT count(*) k FROM h
        GROUP BY city_code, centre_type, capacity, prior_fails, months_since_last, inspection_date, checklist_version, followup_scheduled, label_fail HAVING count(*) > 1)""").fetchone()[0]
    print(f"\n2. Exact duplicates (all columns except row_id): {dup} rows ({100 * dup / n:.1f}%)")
    a_n, agree = con.execute("SELECT count(*), sum(CASE WHEN label_first_inspector = label_second_inspector THEN 1 ELSE 0 END) FROM audit").fetchone()
    p1 = con.execute("SELECT avg(label_first_inspector), avg(label_second_inspector) FROM audit").fetchone()
    po = agree / a_n
    pe = p1[0] * p1[1] + (1 - p1[0]) * (1 - p1[1])
    kappa = (po - pe) / (1 - pe)
    print(f"\n3. Label agreement on {a_n} re-inspected visits: {agree} agree ({100 * po:.1f}%), Cohen's kappa {kappa:.2f}")
    print("\n4. Fail rate by a column recorded after the visit")
    show(*query(con, "SELECT followup_scheduled, count(*) AS rows, round(100.0 * avg(label_fail), 1) AS fail_pct FROM h GROUP BY 1 ORDER BY 1"))
    print("\n5. Rows by checklist version (the 2019 checklist was replaced on 2024-07-01)")
    show(*query(con, "SELECT checklist_version, count(*) AS rows, round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct FROM h GROUP BY 1 ORDER BY 1"))


def words(t: str) -> list[str]:
    return re.findall(r"[\w؀-ۿ]+", t)


def shingles(t: str, k: int = 3) -> set:
    w = words(t)
    return {" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def docs() -> None:
    with open(AI / "docs_index.csv", encoding="utf-8") as f:
        idx = list(csv.DictReader(f))
    body = {d["doc_id"]: (AI / "docs" / f"{d['doc_id']}.txt").read_text(encoding="utf-8").split("\n", 2)[-1] for d in idx}
    r = date.fromisoformat(REPORT_DATE)
    print(f"documents: {len(idx)}\n")
    near = []
    for i, a in enumerate(idx):
        for b in idx[i + 1:]:
            sa, sb = shingles(body[a["doc_id"]]), shingles(body[b["doc_id"]])
            j = len(sa & sb) / len(sa | sb)
            if j >= 0.5:
                near.append([a["doc_id"], b["doc_id"], f"{j:.2f}"])
    print("1. Near duplicates (shared three-word runs, Jaccard 0.5 or more)")
    show(["doc", "doc", "similarity"], near)
    sup = [[d["doc_id"], d["title"], d["superseded_by"]] for d in idx if d["superseded_by"]]
    print("\n2. Superseded versions still in the collection")
    show(["doc", "title", "superseded by"], sup)
    print("\n3. Topics where current documents state different numbers")
    by_topic = defaultdict(list)
    for d in idx:
        if not d["superseded_by"]:
            by_topic[d["topic"]].append(d)
    conflicts = []
    num_words = {"ستة": "6", "ثمانية": "8", "عشرة": "10", "ثلاثة": "3", "سنتين": "2", "ثلاثين": "30", "تسعين": "90"}
    for topic, ds in sorted(by_topic.items()):
        seen = {}
        for d in ds:
            t = body[d["doc_id"]]
            nums = sorted(set(re.findall(r"\d+", t)) | {v for k, v in num_words.items() if k in t})
            seen[d["doc_id"]] = ",".join(nums)
        if len(set(v for v in seen.values() if v)) > 1:
            conflicts.append([topic, " | ".join(f"{k}: {v}" for k, v in seen.items() if v)])
    show(["topic", "numbers per current document"], conflicts)
    print("\n4. Currency: no effective date, or not reviewed in the 12 months before the report date")
    stale = []
    for d in idx:
        why = []
        if not d["effective_from"]:
            why.append("no effective date")
        if (r - date.fromisoformat(d["last_reviewed"])).days > 365:
            why.append(f"last reviewed {d['last_reviewed']}")
        if d["effective_from"] and d["last_reviewed"] < d["effective_from"]:
            why.append("reviewed before it took effect")
        if why:
            stale.append([d["doc_id"], d["title"], "; ".join(why)])
    show(["doc", "title", "why"], stale)
    print("\n5. Personal data markers (an identity number, a mobile number, a home address)")
    marks = ["هويتي", "رقم جوالي", "عنوان منزلي", "رقم الهوية"]
    pd_rows = [[d["doc_id"], d["title"], ", ".join(m for m in marks if m in body[d["doc_id"]])] for d in idx if any(m in body[d["doc_id"]] for m in marks)]
    show(["doc", "title", "markers"], pd_rows)


def main() -> None:
    utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["table", "docs"])
    a = ap.parse_args()
    table() if a.what == "table" else docs()


if __name__ == "__main__":
    main()
