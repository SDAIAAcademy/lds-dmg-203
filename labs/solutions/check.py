"""Run every lab's reference solution and assert its numbers. From the labs/ folder:

    uv run solutions/check.py            # every lab, the pre-work and the assessor's tool
    uv run solutions/check.py 2.1 3.2    # some of them

It recomputes each key from the case files with the lab kit (DuckDB), prints the numbers the
debrief slides quote, and prints PASS per lab. It also checks that the supplied starting files
still hold their planted problems. No lab calls a language model. Outputs go to out/, which git
ignores and which you may delete afterwards.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LABS / "kit"))
from common import FILES, connect, csv_view, utf8  # noqa: E402

REF = LABS / "solutions" / "reference"
OUT = LABS / "out"
KEY = json.loads((REF / "seeded_defects.json").read_text(encoding="utf-8"))
SUBSIDY = {"SRW": 350, "GHD": 350, "ARK": 350, "SHW": 420, "ATB": 420}


def run(*args: str) -> str:
    p = subprocess.run([sys.executable, *args], cwd=LABS, capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def lab_1_1() -> None:
    con = connect()
    csv_view(con, "report", FILES / "day1" / "report_2026_10.csv")
    q = """WITH one AS (SELECT c.city_code, l.centre_id, max(l.capacity_licensed) cap
                        FROM licences l JOIN centres c USING (centre_id)
                        WHERE l.status = 'ACTIVE' AND l.expiry_date >= DATE '2026-10-31' GROUP BY 1, 2)
           SELECT r.city_code, r.active_licences, count(o.centre_id), r.licensed_places, sum(o.cap)
           FROM report r JOIN one o USING (city_code) GROUP BY ALL ORDER BY 1"""
    res = con.execute(q).fetchall()
    gap_l = sum(r[1] - r[2] for r in res)
    gap_p = sum(r[3] - r[4] for r in res)
    monthly = sum((r[3] - r[4]) * SUBSIDY[r[0]] for r in res)
    for r in res:
        print(f"  {r[0]}: report {r[1]} / {r[3]}, definition {r[2]} / {r[4]}, gap {r[1] - r[2]} / {r[3] - r[4]}")
    print(f"  total gap: {gap_l} licences, {gap_p} places; subsidy {monthly:,} a month, {3 * monthly:,} a quarter")
    assert gap_l == KEY["defects"]["D7"]["rows"] + KEY["defects"]["D8"]["rows"], gap_l
    assert all(r[1] > r[2] and r[3] > r[4] for r in res)
    assert (gap_l, gap_p, monthly) == (78, 4300, 1543010), (gap_l, gap_p, monthly)


def lab_1_2() -> None:
    cde = rows(FILES / "day1" / "cde_list.csv")
    req = {r["req_id"]: r for r in rows(FILES / "day1" / "requirements.csv")}
    dic = {f"{r['table']}.{r['column']}" for r in rows(FILES / "day1" / "data_dictionary.csv")}
    assert len(cde) == 10 and len({r["element"] for r in cde}) == 10
    for r in cde:
        served = r["requirements_served"].split()
        assert r["element"] in dic, r["element"]
        assert all(s in req for s in served), served
        assert len(served) >= 2, r
        assert r["data_owner"] and r["business_steward"], r
    print("  ten elements, each serving two requirements or more, each with an owner and a steward")


def lab_1_3() -> None:
    cat = rows(FILES / "day2" / "rules_reference.csv")
    cde = {r["element"] for r in rows(FILES / "day1" / "cde_list.csv")}
    review = rows(REF / "suggestions_review.csv")
    assert len(cat) >= 15
    assert {r["cde"] for r in cat} == cde, "every critical element has a rule"
    for r in cat:
        assert r["threshold_pct"] and r["rule_owner"] and r["data_owner"] and r["frequency"], r["rule_id"]
        assert float(r["escalate_below_pct"]) <= float(r["threshold_pct"]), r["rule_id"]
    dims = {r["dimension"] for r in cat}
    assert dims == {"الدقة", "الاكتمال", "الاتساق", "التوقيت", "الصلاحية", "التفرد"}, dims
    calls = {r["suggestion_id"]: r["decision"] for r in review}
    assert len(calls) == 8 and set(calls.values()) == {"قبول", "تعديل", "رفض"}, calls
    assert calls["S1"] == "رفض" and calls["S2"] == "رفض" and calls["S4"] == "قبول"
    print(f"  {len(cat)} rules over {len(cde)} elements and six dimensions; suggestions: "
          + ", ".join(f"{k} {v}" for k, v in calls.items()))


def lab_1_4() -> None:
    con = connect()
    csv_view(con, "h", FILES / "day1" / "rule_history.csv")
    base = dict(con.execute("SELECT rule_id, round(100.0 * sum(rows_passed) / sum(rows_checked), 2) FROM h GROUP BY 1").fetchall())
    ref = rows(REF / "thresholds_reference.csv")
    for r in ref:
        assert abs(float(r["baseline_pct"]) - base[r["rule_id"]]) < 0.01, (r["rule_id"], base[r["rule_id"]])
    h1 = next(r for r in ref if r["rule_id"] == "H1")
    below = con.execute(f"SELECT count(*) FROM h WHERE rule_id = 'H1' AND 100.0 * rows_passed / rows_checked < {h1['escalate_below_pct']}").fetchone()[0]
    fails = [r["rule_id"] for r in ref if float(r["baseline_pct"]) < float(r["threshold_pct"])]
    exc = rows(REF / "exceptions_reference.csv")
    assert len(exc) == 2 and all(e["expires"] and e["owner"] for e in exc)
    print("  baselines: " + ", ".join(f"{k} {v}" for k, v in sorted(base.items())))
    print(f"  below threshold today: {fails}; months of H1 below its escalation line: {below}")
    assert fails == ["H1"] and below == 2, (fails, below)


def defects(labno: str) -> None:
    con = connect()
    found = 0
    for r in rows(REF / "defect_log_reference.csv"):
        if r["lab"] != labno:
            continue
        n = con.execute(r["query"]).fetchone()[0]
        assert n == int(r["rows_affected"]), (r["defect_no"], n)
        found += 1
        print(f"  {r['defect_no']:4} {r['table']}.{r['column']}: {n}")
    assert found == (5 if labno == "2.1" else 5)


def lab_2_1() -> None:
    defects("2.1")
    out = run("kit/profile.py", "centres")
    assert "99999 ×31" in out and "غير محدد" in out, "the profile no longer shows the planted shapes"


def lab_2_2() -> None:
    defects("2.2")
    hidden = KEY["defects"]["D9"]["rows"] - 56
    print(f"  D9 in all: {KEY['defects']['D9']['rows']} centres, {hidden} of them behind a five-digit postal code (D2)")
    con = connect()
    csv_view(con, "fv", FILES / "day2" / "field_verification.csv")
    wrong = con.execute("SELECT count(*) FROM fv JOIN centres USING (centre_id) WHERE verified_city_code <> city_code").fetchone()[0]
    out = run("kit/sample_estimate.py", "--n", "60", "--failed", str(wrong), "--population", "1000")
    print("  " + out.strip().replace("\n", "\n  "))
    assert wrong == KEY["field_sample_wrong"] == 4
    assert "2.6% to 15.9%" in out, out


def lab_2_3() -> None:
    log = OUT / "check_2_3.csv"
    start = run("kit/run_checks.py", "files/day2/checks_start.yml", "--catalogue", "files/day2/rules_reference.csv", "--out", str(log))
    assert "NOT RUN 6" in start, start[-300:]
    out = run("kit/run_checks.py", "solutions/reference/checks_reference.yml", "--catalogue", "files/day2/rules_reference.csv", "--out", str(log))
    got = {r["rule_id"]: r for r in rows(log)}
    assert len(got) == 20 and all(r["result"] in ("PASS", "FAIL") for r in got.values())
    expect = {"R04": 41, "R07": 37, "R08": 14, "R12": 306, "R14": 31, "R15": 26, "R19": 17}
    for rid, n in expect.items():
        assert int(got[rid]["rows_failed"]) == n, (rid, got[rid]["rows_failed"])
    failing = sorted(k for k, v in got.items() if v["result"] == "FAIL")
    print(f"  20 of 20 rules ran; failing: {' '.join(failing)}")
    assert len(failing) == 11
    ref = {r["rule_id"]: r for r in rows(FILES / "day2" / "run_log_reference.csv")}
    assert all(ref[k]["rows_failed"] == got[k]["rows_failed"] for k in got), "run_log_reference.csv is stale: run _tools/derive_files.py"
    # D4 (submission dates) and D6 rows aside, what no catalogue rule covers: the 1900 dates
    assert not any(r["cde"].startswith("applications.") for r in rows(FILES / "day2" / "rules_reference.csv"))


def lab_2_4() -> None:
    out = run("kit/scorecard.py", "files/day2/run_log_reference.csv", "--out", str(OUT / "scorecard.csv"))
    print("  " + "\n  ".join(out.splitlines()[:3]))
    assert "Headline A, rows passed: 97.5%" in out and "9 of 20 rules" in out, out[:300]
    draft = rows(FILES / "day2" / "draft_scorecard.csv")
    assert draft[0]["النسبة %"] == "97.5" and draft[0]["التقدير"] == "ممتاز"


def lab_3_1() -> None:
    issues = {r["issue_id"]: r for r in rows(FILES / "day3" / "issue_log.csv")}
    tri = {r["issue_id"]: r for r in rows(REF / "issue_triage_reference.csv")}
    assert set(tri) == set(issues)
    dups = sorted(k for k, v in tri.items() if v["duplicate_of"])
    assert dups == ["ISS-103", "ISS-106", "ISS-110"] and {tri[k]["duplicate_of"] for k in dups} == {"ISS-101"}
    unique = [v for v in tri.values() if not v["duplicate_of"]]
    resolved = [v for v in unique if v["status_after_review"] == "مغلقة"]
    overdue = [v for v in unique if v["plan_overdue_on_2026_10_31"] == "Y"]
    print(f"  unique problems {len(unique)}, resolved {len(resolved)}, plan overdue {len(overdue)}")
    print("  severities: " + ", ".join(f"{k} {v['severity']}" for k, v in sorted(tri.items()) if not v["duplicate_of"]))
    assert (len(unique), len(resolved), len(overdue)) == (9, 1, 7)
    assert tri["ISS-104"]["status_after_review"] == "مفتوحة" and tri["ISS-112"]["severity"] == "حرجة"


def lab_3_2() -> None:
    con = connect()
    q = """WITH last AS (SELECT * FROM applications WHERE decision = 'APPROVED'
                         QUALIFY row_number() OVER (PARTITION BY centre_id ORDER BY submitted_at DESC) = 1)
           SELECT a.channel, coalesce(a.form_version, '-'), coalesce(a.premises_same_as_owner, '-'), c.centre_type, count(*),
                  sum(CASE WHEN length(c.postal_code) = 6 AND substr(c.postal_code, 1, 2) <> ci.postal_prefix THEN 1 ELSE 0 END)
           FROM centres c JOIN cities ci USING (city_code) JOIN last a USING (centre_id) GROUP BY ALL ORDER BY 1, 2, 3, 4"""
    res = con.execute(q).fetchall()
    bad = [r for r in res if r[5]]
    for r in res:
        print(f"  {r[0]:8} {r[1]:3} {r[2]} {r[3]:7} centres {r[4]:4} mismatched {r[5]}")
    assert len(bad) == 1 and bad[0][:4] == ("PORTAL", "v3", "Y", "CENTRE") and bad[0][5] == 56, bad
    csv_view(con, "w", FILES / "day3" / "address_weekly.csv")
    before, after = con.execute("""SELECT
        round(100.0 * sum(city_postal_mismatch) FILTER (WHERE week_starting < DATE '2025-02-24') / sum(approved_applications) FILTER (WHERE week_starting < DATE '2025-02-24'), 1),
        round(100.0 * sum(city_postal_mismatch) FILTER (WHERE week_starting >= DATE '2025-02-24') / sum(approved_applications) FILTER (WHERE week_starting >= DATE '2025-02-24'), 1) FROM w""").fetchone()
    moved = con.execute("SELECT count(*) FROM inspections WHERE reassigned = 'Y'").fetchone()[0]
    print(f"  weekly mismatch share: {before}% before v3, {after}% since; inspections reassigned: {moved}")
    assert (before, after, moved) == (0.0, 8.1, 66)


def lab_3_3() -> None:
    out = run("kit/prerelease.py", "files/day3/open_data_extract.csv")
    got = {l.split()[0]: l for l in out.splitlines() if l[:2] in ("P1", "P2", "P3", "P4", "P5", "P6")}
    print("  " + "\n  ".join(got.values()))
    assert "FAIL" in got["P1"] and "FAIL" in got["P2"] and "FAIL" in got["P6"] and "PASS" in got["P3"]
    assert "4 checks failed" in out


def lab_3_4() -> None:
    t = run("kit/ai_fitness.py", "table")
    d = run("kit/ai_fitness.py", "docs")
    for line in t.splitlines():
        if line.startswith(("SHW        HOME", "ATB        HOME", "2. ", "3. ", "N  ", "Y  ", "2019")):
            print("  " + line)
    assert "SHW        HOME         25    1.1        7.4             0.15" in t and "ATB        HOME         30" in t
    assert "140 rows (6.0%)" in t and "66 agree (82.5%)" in t and "kappa 0.60" in t
    assert "Y                   341   81.5" in t and "2019               926   39.9" in t
    assert "DOC-04  DOC-05  1.00" in d and "DOC-19" in d and "staff_ratio  DOC-02: 2,6 | DOC-03: 2,8" in d
    print("  documents: 2 near-duplicate pairs, 4 superseded, 1 real conflict (staff ratio), 9 currency flags, 1 with personal data")


def prework() -> None:
    out = run("kit/check_prework.py", "solutions/prework_answers.sql")
    assert "10 of 10 correct" in out
    blank = run("kit/check_prework.py", "files/prework/sql_drills.sql")
    assert "0 of 10 correct" in blank
    print("  the reference answers pass 10 of 10; the blank sheet 0 of 10")


def assessor() -> None:
    base = {r["rule_id"]: int(r["rows_failed"]) for r in rows(FILES / "day2" / "run_log_reference.csv")}
    expect = {"nulls": "R17", "duplicates": "R01", "codes": "R03", "orphans": "R19", "range": "R08", "stale": "R04", "postal": "R14"}
    for kind, rule in expect.items():
        seeded = OUT / "seeded"
        run("kit/seed_defect.py", "--kind", kind, "--out", str(seeded), "--seed", "11")
        log = OUT / "seeded_log.csv"
        run("kit/run_checks.py", "solutions/reference/checks_reference.yml", "--data", str(seeded), "--out", str(log))
        now = {r["rule_id"]: int(r["rows_failed"]) for r in rows(log)}
        assert now[rule] > base[rule], (kind, rule)
        print(f"  seeded {kind:10} caught by {rule}: {base[rule]} -> {now[rule]} failing rows")
    shutil.rmtree(OUT / "seeded", ignore_errors=True)


LABS_RUN = {"1.1": lab_1_1, "1.2": lab_1_2, "1.3": lab_1_3, "1.4": lab_1_4, "2.1": lab_2_1, "2.2": lab_2_2,
            "2.3": lab_2_3, "2.4": lab_2_4, "3.1": lab_3_1, "3.2": lab_3_2, "3.3": lab_3_3, "3.4": lab_3_4,
            "prework": prework, "assessor": assessor}


def main() -> None:
    utf8()
    OUT.mkdir(exist_ok=True)
    picks = sys.argv[1:] or list(LABS_RUN)
    for k in picks:
        print(f"Lab {k}")
        LABS_RUN[k]()
        print(f"Lab {k}: PASS")
    total = sum(v["rows"] for v in KEY["defects"].values())
    print(f"\nall PASS ({len(picks)} checked); seeded defects: {len(KEY['defects'])} kinds, {total} rows")


if __name__ == "__main__":
    main()
