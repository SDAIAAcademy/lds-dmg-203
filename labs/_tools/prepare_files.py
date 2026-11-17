"""Write the synthetic case files of LDS-DMG-203 (Akmam Childcare Licensing Agency).

    uv run labs/_tools/prepare_files.py

Standard library only, seed 203, the same bytes on every run. Writes CSV files under labs/files/
and the trainer's key labs/solutions/reference/seeded_defects.json. Every name, number, code and
address is invented. The five cities, their districts and the postal-code format are fictional.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
FILES = LABS / "files"
REF = LABS / "solutions" / "reference"
R = date(2026, 10, 31)  # the report month ends here
V3 = date(2025, 3, 2)  # portal form version 3 goes live
TABLET = date(2025, 7, 1)  # one office moves to a new inspection app

CITIES = [  # code, Arabic name, postal prefix, centres, share of home nurseries
    ("SRW", "السرو", "01", 300, 0.28),
    ("GHD", "الغضا", "02", 240, 0.30),
    ("ARK", "الأراك", "03", 200, 0.35),
    ("SHW", "الشوحط", "04", 140, 0.55),
    ("ATB", "الأثاب", "05", 120, 0.55),
]
PREFIX = {c[0]: c[2] for c in CITIES}
NAME = {c[0]: c[1] for c in CITIES}
DISTRICTS = 8


def d(s: str) -> date:
    return date.fromisoformat(s)


def rand_date(rng: random.Random, a: date, b: date) -> date:
    return a + timedelta(days=rng.randint(0, (b - a).days))


def write(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])


def licensing(rng: random.Random) -> dict:
    """The four lab tables, with the ten seeded defects."""
    centres, apps, lics, insp = [], [], [], []
    key: dict = {}
    cid = 0
    for city, _, prefix, n, home_share in CITIES:
        for _ in range(n):
            cid += 1
            ctype = "HOME" if rng.random() < home_share else "CENTRE"
            dist = rng.randint(1, DISTRICTS)
            other = [c[0] for c in CITIES if c[0] != city]
            owner_city = city if (ctype == "HOME" or rng.random() < 0.62) else rng.choice(other)
            cap = rng.randint(4, 10) if ctype == "HOME" else rng.choice(range(20, 151, 5))
            centres.append({
                "centre_id": f"C-{cid:04d}", "centre_type": ctype, "city": city, "district": dist,
                "owner_city": owner_city, "owner_district": rng.randint(1, DISTRICTS) if owner_city != city else dist,
                "building_no": rng.randint(1000, 9999), "postal": f"{prefix}{dist:02d}{rng.randint(0, 99):02d}",
                "owner_id": f"OWN-{rng.randint(10000, 99999)}", "opened": rand_date(rng, d("2019-01-01"), d("2026-09-15")),
                "capacity": cap, "closes": rng.random() < 0.2,
            })
    # applications and licences, one chain per centre
    aid = lid = 0
    for c in centres:
        when = c["opened"] - timedelta(days=rng.randint(20, 60))
        kind = "NEW"
        chain = 0
        rec_city, rec_dist = c["city"], c["district"]
        while when <= R:
            aid += 1
            portal = rng.random() < 0.6 if when >= d("2021-01-01") else rng.random() < 0.3
            channel = "PORTAL" if portal else rng.choice(["COUNTER", "COUNTER", "APP"])
            version = ("v3" if when >= V3 else "v2") if portal else None
            same = None
            if version == "v3":  # only v3 has the box
                if c["centre_type"] == "HOME":
                    same = "Y"
                else:
                    same = "Y" if rng.random() < 0.58 else "N"  # the box is ticked when the form opens
            decided = when + timedelta(days=rng.randint(4, 35))
            decision = "APPROVED" if decided <= R else "PENDING"
            # the address the record ends up with: the nightly job copies every approved application
            if decision == "APPROVED":
                if same == "Y" and c["centre_type"] == "CENTRE":
                    rec_city, rec_dist = c["owner_city"], c["owner_district"]
                else:
                    rec_city, rec_dist = c["city"], c["district"]
            app = {
                "application_id": f"A-{aid:06d}", "centre_id": c["centre_id"], "app_type": kind,
                "channel": channel, "form_version": version, "premises_same_as_owner": same,
                "submitted_at": when.isoformat(), "decision": decision,
                "decision_date": decided.isoformat() if decision == "APPROVED" else None,
                "capacity_requested": c["capacity"],
            }
            apps.append(app)
            if decision != "APPROVED":
                break
            lid += 1
            lics.append({
                "licence_no": f"AKM-L-{decided.year}-{lid:05d}", "application_id": app["application_id"],
                "centre_id": c["centre_id"], "issue_date": decided, "expiry_date": decided + timedelta(days=730),
                "capacity_licensed": c["capacity"], "status": None,
            })
            chain += 1
            exp = decided + timedelta(days=730)
            if c["closes"] and chain >= 1 and rng.random() < 0.6:
                break
            when = exp - timedelta(days=rng.randint(10, 45))
            kind = "RENEWAL"
        c["rec_city"], c["rec_dist"] = rec_city, rec_dist
    # statuses as of the report date
    by_centre: dict[str, list] = {}
    for lic in lics:
        by_centre.setdefault(lic["centre_id"], []).append(lic)
    for chain in by_centre.values():
        for i, lic in enumerate(chain):
            if i < len(chain) - 1 and chain[i + 1]["issue_date"] <= R:
                lic["status"] = "RENEWED"
            elif lic["expiry_date"] < R:
                lic["status"] = "EXPIRED"
            else:
                u = rng.random()
                lic["status"] = "SUSPENDED" if u < 0.015 else "CANCELLED" if u < 0.025 else "ACTIVE"
    # rejected and withdrawn applications without a centre
    for _ in range(160):
        aid += 1
        when = rand_date(rng, d("2020-01-01"), d("2026-10-20"))
        portal = rng.random() < 0.55
        apps.append({
            "application_id": f"A-{aid:06d}", "centre_id": None, "app_type": "NEW",
            "channel": "PORTAL" if portal else "COUNTER", "form_version": ("v3" if when >= V3 else "v2") if portal else None,
            "premises_same_as_owner": ("N" if portal and when >= V3 else None), "submitted_at": when.isoformat(),
            "decision": rng.choice(["REJECTED", "REJECTED", "WITHDRAWN"]),
            "decision_date": (when + timedelta(days=rng.randint(5, 40))).isoformat(),
            "capacity_requested": rng.choice(range(20, 101, 5)),
        })
    # inspections: within 90 days of each issue date, then yearly while the licence runs
    iid = 0
    cmap = {c["centre_id"]: c for c in centres}
    for lic in lics:
        c = cmap[lic["centre_id"]]
        t = lic["issue_date"] + timedelta(days=rng.randint(20, 90))
        end = min(lic["expiry_date"], R)
        if lic["status"] in ("RENEWED",):
            end = min(end, lic["expiry_date"])
        while t <= end:
            iid += 1
            u = rng.random()
            outcome = "PASS" if u < 0.78 else "COND" if u < 0.93 else "FAIL"
            score = rng.randint(80, 100) if outcome == "PASS" else rng.randint(60, 79) if outcome == "COND" else rng.randint(20, 59)
            # the office comes from the recorded city; the record is wrong only after the v3 error
            app = next(a for a in apps if a["application_id"] == lic["application_id"])
            wrong = (app["form_version"] == "v3" and app["premises_same_as_owner"] == "Y"
                     and c["centre_type"] == "CENTRE" and c["owner_city"] != c["city"])
            office = c["owner_city"] if wrong else c["city"]
            lag = rng.randint(0, 4) if rng.random() < 0.9 else rng.randint(6, 20)
            insp.append({
                "inspection_id": f"I-{iid:06d}", "licence_no": lic["licence_no"], "inspection_date": t,
                "entered_at": t + timedelta(days=lag), "inspector_id": f"INS-{rng.randint(1, 48):02d}",
                "office_city": office, "reassigned": "Y" if wrong else "N", "outcome": outcome, "score": score,
                "followup_scheduled": "Y" if outcome != "PASS" else "N",
            })
            t = t + timedelta(days=rng.randint(330, 400))
    insp = [i for i in insp if i["inspection_date"] <= R]

    # ---- seeded defects ----
    actives = [l for l in lics if l["status"] == "ACTIVE"]
    expired = [l for l in lics if l["status"] == "EXPIRED"]
    # D1: capacity sentinel 999
    d1 = rng.sample([l for l in lics if l["status"] in ("ACTIVE", "RENEWED", "EXPIRED")], 14)
    for l in d1:
        l["capacity_licensed"] = 999
    # D7: renewal entered twice: a second licence row for the same application
    d7 = rng.sample([l for l in actives if l not in d1], 37)
    dups = []
    for l in d7:
        lid += 1
        dup = dict(l)
        dup["licence_no"] = f"AKM-L-{l['issue_date'].year}-{lid:05d}"
        dups.append(dup)
    lics.extend(dups)
    # D8: active although expired (the nightly expiry job skipped closed centres)
    d8 = rng.sample([l for l in expired if l not in d1], 41)
    for l in d8:
        l["status"] = "ACTIVE"
    # D10: home nurseries licensed above ten places
    homes = [l for l in lics if cmap[l["centre_id"]]["centre_type"] == "HOME" and l not in d1 and l not in dups]
    d10 = rng.sample(homes, 12)
    for l in d10:
        l["capacity_licensed"] = rng.randint(14, 25)
    # D2: leading zero of the postal code lost
    d2 = rng.sample(centres, 31)
    # D5: district placeholder
    d5 = rng.sample([c for c in centres if c not in d2], 26)
    # D4: migration default on the submission date
    counter_apps = [a for a in apps if a["channel"] == "COUNTER" and a["submitted_at"] < "2021-01-01"]
    d4 = rng.sample(counter_apps, 9)
    for a in d4:
        a["submitted_at"] = "1900-01-01"
    # D3: the new inspection app of one office writes words, not codes
    words = {"PASS": "compliant", "COND": "conditional", "FAIL": "non_compliant"}
    d3 = [i for i in insp if i["office_city"] == "GHD" and i["inspection_date"] >= TABLET]
    for i in d3:
        i["outcome"] = words[i["outcome"]]
    # D6: inspections pointing to licence numbers that do not exist (two digits swapped)
    d6 = rng.sample([i for i in insp if i not in d3], 23)
    for i in d6:
        n = i["licence_no"]
        i["licence_no"] = n[:-2] + n[-1] + n[-2] if n[-1] != n[-2] else n[:-1] + str((int(n[-1]) + 1) % 10)
    known = {l["licence_no"] for l in lics}
    d6 = [i for i in d6 if i["licence_no"] not in known]

    # D9: centres whose recorded city is not the city of the premises
    d9 = [c for c in centres if c["rec_city"] != c["city"]]

    first_issue: dict[str, date] = {}
    for l in lics:
        if l["centre_id"] not in first_issue or l["issue_date"] < first_issue[l["centre_id"]]:
            first_issue[l["centre_id"]] = l["issue_date"]

    def opened_of(c: dict) -> str:
        """A centre opens after its first licence: a week later, or never yet when none was issued."""
        f = first_issue.get(c["centre_id"])
        return (f + timedelta(days=7)).isoformat() if f else ""

    rows_c = []
    for c in centres:
        postal = c["postal"]
        if c["rec_city"] != c["city"]:
            dist_code = f"{c['rec_city']}-{c['rec_dist']:02d}"
        else:
            dist_code = f"{c['city']}-{c['district']:02d}"
        if c in d2:
            postal = postal.lstrip("0")
        if c in d5:
            dist_code = "غير محدد"
        rows_c.append([c["centre_id"], c["centre_type"], c["rec_city"], dist_code, c["building_no"], postal,
                       c["owner_id"], opened_of(c)])
    rows_a = [[a[k] for k in ("application_id", "centre_id", "app_type", "channel", "form_version",
                               "premises_same_as_owner", "submitted_at", "decision", "decision_date",
                               "capacity_requested")] for a in apps]
    rng.shuffle(lics)
    rows_l = [[l["licence_no"], l["application_id"], l["centre_id"], l["issue_date"].isoformat(),
               l["expiry_date"].isoformat(), l["status"], l["capacity_licensed"]] for l in lics]
    rows_i = [[i["inspection_id"], i["licence_no"], i["inspection_date"].isoformat(), i["entered_at"].isoformat(),
               i["inspector_id"], i["office_city"], i["reassigned"], i["outcome"], i["score"],
               i["followup_scheduled"]] for i in insp]
    data = FILES / "data"
    write(data / "centres.csv", ["centre_id", "centre_type", "city_code", "district_code", "building_no",
                                 "postal_code", "owner_id", "opened_date"], rows_c)
    write(data / "applications.csv", ["application_id", "centre_id", "app_type", "channel", "form_version",
                                      "premises_same_as_owner", "submitted_at", "decision", "decision_date",
                                      "capacity_requested"], rows_a)
    write(data / "licences.csv", ["licence_no", "application_id", "centre_id", "issue_date", "expiry_date",
                                  "status", "capacity_licensed"], rows_l)
    write(data / "inspections.csv", ["inspection_id", "licence_no", "inspection_date", "entered_at",
                                     "inspector_id", "office_city", "reassigned", "outcome", "score",
                                     "followup_scheduled"], rows_i)
    write(data / "cities.csv", ["city_code", "city_name", "postal_prefix", "inspection_office"],
          [[c[0], c[1], c[2], f"OFF-{c[0]}"] for c in CITIES])
    write(data / "districts.csv", ["district_code", "city_code", "district_name", "postal_digits"],
          [[f"{c[0]}-{k:02d}", c[0], f"الحي {k} في {c[1]}", f"{c[2]}{k:02d}"] for c in CITIES for k in range(1, DISTRICTS + 1)])
    write(data / "codes_outcome.csv", ["code", "meaning"], [["PASS", "مستوفٍ"], ["COND", "مستوفٍ بشروط"], ["FAIL", "غير مستوفٍ"]])

    key["defects"] = {
        "D1": {"table": "licences", "column": "capacity_licensed", "rows": len(d1)},
        "D2": {"table": "centres", "column": "postal_code", "rows": len(d2)},
        "D3": {"table": "inspections", "column": "outcome", "rows": len(d3)},
        "D4": {"table": "applications", "column": "submitted_at", "rows": len(d4)},
        "D5": {"table": "centres", "column": "district_code", "rows": len(d5)},
        "D6": {"table": "inspections", "column": "licence_no", "rows": len(d6)},
        "D7": {"table": "licences", "column": "application_id", "rows": len(dups)},
        "D8": {"table": "licences", "column": "status+expiry_date", "rows": len(d8)},
        "D9": {"table": "centres", "column": "city_code+postal_code", "rows": len(d9)},
        "D10": {"table": "licences+centres", "column": "capacity_licensed+centre_type", "rows": len(d10)},
    }
    key["d9_centres"] = sorted(c["centre_id"] for c in d9)
    key["d2_centres"] = sorted(c["centre_id"] for c in d2)
    key["true_city"] = {c["centre_id"]: c["city"] for c in centres}
    key["counts"] = {"centres": len(rows_c), "applications": len(rows_a), "licences": len(rows_l), "inspections": len(rows_i)}
    return {"centres": centres, "cmap": cmap, "lics": lics, "apps": apps, "insp": insp, "key": key}


def monthly_report(lab: dict) -> None:
    """The October report as published: every ACTIVE row, grouped by the recorded city."""
    rows: dict[str, list[int]] = {c[0]: [0, 0] for c in CITIES}
    cm = lab["cmap"]
    for l in lab["lics"]:
        if l["status"] == "ACTIVE":
            city = cm[l["centre_id"]]["rec_city"]
            rows[city][0] += 1
            rows[city][1] += l["capacity_licensed"]
    write(FILES / "day1" / "report_2026_10.csv", ["city_code", "city_name", "active_licences", "licensed_places"],
          [[k, NAME[k], v[0], v[1]] for k, v in rows.items()])


def rule_history(rng: random.Random) -> None:
    """Twelve monthly results of six rules already run by the Agency (none on a seeded defect)."""
    months = [f"{y}-{m:02d}" for y, m in [(2025, 11), (2025, 12)] + [(2026, k) for k in range(1, 11)]]
    rules = [  # id, element, dimension, rows per month, typical pass rate, spread
        ("H1", "inspections.entered_at", "التوقيت", 210, 0.905, 0.025),
        ("H2", "licences.licence_no", "الصلاحية", 120, 0.999, 0.001),
        ("H3", "licences.expiry_date", "الاكتمال", 120, 1.0, 0.0),
        ("H4", "inspections.score", "الصلاحية", 210, 0.996, 0.004),
        ("H5", "applications.capacity_requested", "الاكتمال", 140, 0.975, 0.012),
        ("H6", "inspections.inspector_id", "الاكتمال", 210, 0.994, 0.004),
    ]
    rows = []
    for rid, el, dim, n, p, s in rules:
        for m in months:
            q = min(1.0, max(0.0, rng.gauss(p, s)))
            passed = round(n * q) if s else n
            rows.append([rid, el, dim, m, n, passed])
    write(FILES / "day1" / "rule_history.csv", ["rule_id", "element", "dimension", "month", "rows_checked", "rows_passed"], rows)


def field_sample(rng: random.Random, lab: dict) -> None:
    """Inspectors verified the premises city of 60 randomly drawn centres on site."""
    ids = rng.sample([c["centre_id"] for c in lab["centres"]], 60)
    cm = lab["cmap"]
    write(FILES / "day2" / "field_verification.csv", ["centre_id", "verified_city_code", "visit_month"],
          [[i, cm[i]["city"], rng.choice(["2026-08", "2026-09", "2026-10"])] for i in sorted(ids)])
    lab["key"]["field_sample_wrong"] = sum(1 for i in ids if cm[i]["rec_city"] != cm[i]["city"])


def issue_log(lab: dict) -> None:
    """Twelve issues as they reached the data management office."""
    rows = [
        ["ISS-101", "2026-08-03", "مكتب التفتيش في الغضا", "زيارة لمركز تبيّن أنه في الأراك، أعيد إسنادها", "centres", "", 1, "مفتوحة"],
        ["ISS-102", "2026-08-10", "التقارير", "رقم المقاعد المرخصة في تقرير يوليو أعلى من مجموع طاقة المراكز في الميدان", "licences", "", None, "مفتوحة"],
        ["ISS-103", "2026-08-17", "مكتب التفتيش في السرو", "زيارتان لمركزين مسجلين في السرو وموقعهما في الشوحط", "centres", "", 2, "مفتوحة"],
        ["ISS-104", "2026-08-24", "خدمة العملاء", "مالك يقول إن رخصته منتهية والبوابة تعرضها سارية", "licences", "", 1, "مغلقة"],
        ["ISS-105", "2026-09-01", "فحص آلي", "قيمة نتيجة تفتيش خارج قائمة الرموز", "inspections", "R12", lab["key"]["defects"]["D3"]["rows"], "مفتوحة"],
        ["ISS-106", "2026-09-07", "مكتب التفتيش في الأثاب", "مركز مسجل في الأثاب ورمزه البريدي لمدينة أخرى", "centres", "", 1, "مفتوحة"],
        ["ISS-107", "2026-09-14", "مستخدم الكتالوج", "وصف عمود المقاعد في الكتالوج لا يذكر الوحدة", "licences", "", None, "مفتوحة"],
        ["ISS-108", "2026-09-20", "فحص آلي", "رخصتان سارية لطلب واحد", "licences", "R07", 37, "مفتوحة"],
        ["ISS-109", "2026-09-28", "برنامج الذكاء الاصطناعي", "تاريخ تقديم 1900 في بيانات التدريب المقترحة", "applications", "", 9, "مفتوحة"],
        ["ISS-110", "2026-10-05", "مكتب التفتيش في الغضا", "مركز آخر مسجل في الغضا وموقعه في السرو", "centres", "", 1, "مفتوحة"],
        ["ISS-111", "2026-10-12", "التقارير", "التقرير الشهري تأخر يومين بسبب انتظار ملف التفتيش", "inspections", "", None, "مغلقة"],
        ["ISS-112", "2026-10-19", "الشؤون القانونية", "قائمة المراكز المرسلة لشريك تضمنت عناوين منازل لحضانات منزلية", "centres", "", sum(1 for c in lab["centres"] if c["centre_type"] == "HOME"), "مفتوحة"],
    ]
    write(FILES / "day3" / "issue_log.csv", ["issue_id", "reported_on", "reported_by", "description", "table", "rule_id",
                                             "rows_affected", "status"], rows)


def address_extract(lab: dict) -> None:
    """Weekly count of new or renewed applications whose recorded city differs from the postal area."""
    cm = lab["cmap"]
    weekly: dict[str, list[int]] = {}
    for a in lab["apps"]:
        if a["decision"] != "APPROVED" or not a["centre_id"]:
            continue
        sub = date.fromisoformat(a["submitted_at"]) if a["submitted_at"] != "1900-01-01" else None
        if not sub or sub < d("2024-09-01"):
            continue
        c = cm[a["centre_id"]]
        wrong = (a["form_version"] == "v3" and a["premises_same_as_owner"] == "Y"
                 and c["centre_type"] == "CENTRE" and c["owner_city"] != c["city"])
        monday = sub - timedelta(days=sub.weekday())
        w = weekly.setdefault(monday.isoformat(), [0, 0])
        w[0] += 1
        w[1] += 1 if wrong else 0
    rows = [[k, v[0], v[1]] for k, v in sorted(weekly.items())]
    write(FILES / "day3" / "address_weekly.csv", ["week_starting", "approved_applications", "city_postal_mismatch"], rows)


def open_data(lab: dict) -> None:
    """The extract the reporting team prepared for the open data portal (not yet published)."""
    rows = []
    cm = lab["cmap"]
    seen = set()
    for l in sorted(lab["lics"], key=lambda x: x["centre_id"]):
        if l["status"] != "ACTIVE" or l["centre_id"] in seen:
            continue
        seen.add(l["centre_id"])
        c = cm[l["centre_id"]]
        rows.append([l["centre_id"], "حضانة منزلية" if c["centre_type"] == "HOME" else "مركز رعاية",
                     NAME[c["rec_city"]], f"{c['rec_city']}-{c['rec_dist']:02d}", c["building_no"], c["postal"],
                     l["capacity_licensed"], l["expiry_date"].isoformat()])
    write(FILES / "day3" / "open_data_extract.csv", ["centre_id", "centre_kind", "city", "district_code", "building_no",
                                                     "postal_code", "licensed_places", "licence_expiry"], rows)


def ai_tabular(rng: random.Random, lab: dict) -> None:
    """The table the AI programme wants to train an inspection-risk model on."""
    rows = []
    rid = 0
    pop = {}
    for c in lab["centres"]:
        pop[(c["city"], c["centre_type"])] = pop.get((c["city"], c["centre_type"]), 0) + 1
    # under-sample home nurseries in the two rural cities: they were inspected on paper until 2025
    for c in lab["centres"]:
        rural_home = c["centre_type"] == "HOME" and c["city"] in ("SHW", "ATB")
        n = 1 if rural_home and rng.random() < 0.35 else 0 if rural_home else rng.randint(1, 4)
        for _ in range(n):
            rid += 1
            when = rand_date(rng, d("2023-01-01"), d("2026-09-30"))
            prior = rng.choice([0, 0, 0, 1, 1, 2, 3])
            p_fail = 0.05 + 0.06 * prior + (0.05 if c["centre_type"] == "CENTRE" and c["capacity"] > 100 else 0)
            fail = rng.random() < p_fail
            follow = "Y" if fail else ("Y" if rng.random() < 0.03 else "N")
            checklist = "2024" if when >= d("2024-07-01") else "2019"
            rows.append([f"T-{rid:05d}", c["city"], c["centre_type"], c["capacity"], prior,
                         rng.randint(6, 30), when.isoformat(), checklist, follow, 1 if fail else 0])
    # exact duplicates: rows keyed twice during a migration
    dupe = rng.sample(rows, 140)
    rows.extend([list(r) for r in dupe])
    rng.shuffle(rows)
    write(FILES / "day3" / "ai" / "inspection_history.csv",
          ["row_id", "city_code", "centre_type", "capacity", "prior_fails", "months_since_last", "inspection_date",
           "checklist_version", "followup_scheduled", "label_fail"], rows)
    write(FILES / "day3" / "ai" / "licensed_population.csv", ["city_code", "centre_type", "centres"],
          [[k[0], k[1], v] for k, v in sorted(pop.items())])
    # label audit: a second inspector re-scored 80 sampled inspections
    audit = []
    for k in range(80):
        first = 1 if rng.random() < 0.2 else 0
        second = first if rng.random() < 0.84 else 1 - first
        audit.append([f"T-AUD-{k + 1:02d}", first, second])
    write(FILES / "day3" / "ai" / "label_audit.csv", ["audit_id", "label_first_inspector", "label_second_inspector"], audit)


def ai_documents() -> None:
    """Twenty-four requirement documents the applicant assistant would answer from."""
    topics = [
        ("staff_ratio", "نسبة مقدمي الرعاية إلى الأطفال"),
        ("space", "المساحة الداخلية لكل طفل"),
        ("first_aid", "شهادة الإسعافات الأولية"),
        ("renewal", "مواعيد تجديد الرخصة"),
        ("home_max", "الحد الأعلى لأطفال الحضانة المنزلية"),
        ("fees", "رسوم الطلب"),
        ("inspection", "زيارة التفتيش الأولى"),
        ("documents", "المستندات المطلوبة مع الطلب"),
    ]
    docs = []
    n = 0

    def add(topic: str, title: str, version: str, eff: str | None, review: str, superseded: str | None, body: str) -> None:
        nonlocal n
        n += 1
        did = f"DOC-{n:02d}"
        docs.append([did, topic, title, version, eff or "", review, superseded or ""])
        (FILES / "day3" / "ai" / "docs").mkdir(parents=True, exist_ok=True)
        (FILES / "day3" / "ai" / "docs" / f"{did}.txt").write_text(f"{title}\n\n{body}\n", encoding="utf-8", newline=chr(10))

    add("staff_ratio", "تعميم نسبة مقدمي الرعاية (الإصدار 1)", "1", "2023-01-15", "2024-01-10", "DOC-02",
        "يلتزم المركز بمقدم رعاية واحد لكل ثمانية أطفال في الفئة العمرية من سنتين إلى أربع سنوات.")
    add("staff_ratio", "تعميم نسبة مقدمي الرعاية (الإصدار 2)", "2", "2025-09-01", "2026-08-20", None,
        "يلتزم المركز بمقدم رعاية واحد لكل ستة أطفال في الفئة العمرية من سنتين إلى أربع سنوات، ويسري ذلك على المراكز القائمة عند أول تجديد.")
    add("staff_ratio", "أسئلة شائعة عن التوظيف", "1", "2023-03-01", "2023-03-01", None,
        "س: كم طفلًا لكل مقدم رعاية؟ ج: ثمانية أطفال لكل مقدم رعاية في الفئة من سنتين إلى أربع سنوات.")
    add("space", "اشتراطات المساحة الداخلية", "3", "2024-06-01", "2026-05-30", None,
        "لا تقل المساحة الداخلية المخصصة للعب والنوم عن ثلاثة أمتار مربعة لكل طفل.")
    add("space", "اشتراطات المساحة الداخلية (نسخة الموقع)", "3", "2024-06-01", "2026-05-30", None,
        "لا تقل المساحة الداخلية المخصصة للعب والنوم عن ثلاثة أمتار مربعة لكل طفل.")
    add("first_aid", "شهادة الإسعافات الأولية لمقدمي الرعاية", "2", "2025-01-01", "2026-01-05", None,
        "يحمل كل مقدم رعاية شهادة إسعافات أولية سارية لا يزيد عمرها على سنتين.")
    add("first_aid", "دليل مقدم الرعاية الجديد", "1", None, "2022-11-01", None,
        "ينصح بالحصول على شهادة إسعافات أولية خلال السنة الأولى من العمل.")
    add("renewal", "مواعيد تجديد الرخصة", "2", "2025-04-01", "2026-03-15", None,
        "يقدَّم طلب التجديد قبل انتهاء الرخصة بثلاثين يومًا على الأقل، وتسري الرخصة سنتين من تاريخ إصدارها.")
    add("renewal", "مواعيد تجديد الرخصة (ملخص البوابة)", "2", "2025-04-01", "2026-03-15", None,
        "قدّم طلب التجديد قبل انتهاء الرخصة بثلاثين يومًا على الأقل؛ الرخصة سارية سنتين من الإصدار.")
    add("home_max", "اشتراطات الحضانة المنزلية", "2", "2024-02-01", "2026-02-01", None,
        "لا يزيد عدد الأطفال في الحضانة المنزلية على عشرة أطفال في أي وقت.")
    add("home_max", "اشتراطات الحضانة المنزلية (الإصدار 1)", "1", "2021-05-01", "2022-05-01", "DOC-10",
        "لا يزيد عدد الأطفال في الحضانة المنزلية على ستة أطفال في أي وقت.")
    add("fees", "رسوم الطلبات", "4", "2026-01-01", "2026-10-01", None,
        "لا رسوم على طلب الترخيص الأول للحضانة المنزلية، ورسوم مركز الرعاية تُدفع عند الموافقة.")
    add("fees", "رسوم الطلبات 2024", "3", "2024-01-01", "2024-12-15", "DOC-12",
        "تُدفع رسوم الطلب عند التقديم لكل أنواع المنشآت.")
    add("inspection", "زيارة التفتيش الأولى", "1", "2023-09-01", "2026-04-11", None,
        "تتم الزيارة الأولى خلال تسعين يومًا من إصدار الرخصة، ويُبلَّغ المركز قبلها بيومي عمل.")
    add("inspection", "قائمة التحقق في زيارة التفتيش", "2024", "2024-07-01", "2026-07-01", None,
        "تتضمن قائمة التحقق 42 بندًا في خمسة محاور: السلامة، والصحة، والتغذية، والكوادر، والسجلات.")
    add("inspection", "قائمة التحقق في زيارة التفتيش (قديمة)", "2019", "2019-03-01", "2021-03-01", "DOC-15",
        "تتضمن قائمة التحقق 30 بندًا في أربعة محاور.")
    add("documents", "المستندات المطلوبة مع الطلب", "3", "2025-03-02", "2026-09-01", None,
        "صورة عقد الإيجار أو صك الملكية، ومخطط المكان، وشهادة الدفاع المدني لمراكز الرعاية، وإقرار المالك.")
    add("documents", "المستندات المطلوبة (نموذج ورقي)", "1", None, "2020-06-01", None,
        "صورة عقد الإيجار، ومخطط المكان، وخطاب تعريف من جهة العمل.")
    add("documents", "رسالة متقدم مرفقة بالخطأ", "-", None, "2026-02-14", None,
        "إلى إدارة الترخيص: أرفق لكم صورة هويتي ورقم جوالي وعنوان منزلي لاستكمال طلب الحضانة المنزلية. [حُذفت القيم من نسخة المقرر]")
    add("staff_ratio", "دليل التشغيل لمراكز الرعاية", "2", "2025-10-01", "2026-09-30", None,
        "يُحسب عدد مقدمي الرعاية بحسب التعميم الساري لنسبة مقدمي الرعاية، ويُعلَّق جدول المناوبات في مكان ظاهر.")
    add("space", "المساحات الخارجية", "1", "2024-06-01", "2026-05-30", None,
        "يُستحسن وجود فناء خارجي آمن، ولا يشترط لمراكز الرعاية القائمة قبل 2024.")
    add("renewal", "إيقاف الرخصة وإلغاؤها", "1", "2024-11-01", "2026-06-01", None,
        "توقف الرخصة إذا لم تُعالج ملاحظات زيارة غير مستوفية خلال ثلاثين يومًا.")
    add("fees", "الإعفاءات من الرسوم", "2", "2026-01-01", "2026-10-01", None,
        "تُعفى الحضانات المنزلية في المدن الصغيرة من رسوم التجديد الأول.")
    add("first_aid", "التدريب الإلزامي", "1", "2025-01-01", "2023-12-31", None,
        "ثماني ساعات تدريب سنويًا لكل مقدم رعاية، منها ساعتان في الإسعافات الأولية.")
    write(FILES / "day3" / "ai" / "docs_index.csv",
          ["doc_id", "topic", "title", "version", "effective_from", "last_reviewed", "superseded_by"], docs)


def permits_example(rng: random.Random) -> dict:
    """The parallel domain the slides use: the Agency's caregiver permits register."""
    rows = []
    key = {}
    for k in range(1, 1501):
        issued = rand_date(rng, d("2023-01-01"), d("2026-10-15"))
        expiry = issued + timedelta(days=365 * 2)
        status = "ACTIVE" if expiry >= R else "EXPIRED"
        hours = rng.randint(8, 40)
        aid = (issued + timedelta(days=rng.randint(-600, 0))).isoformat()
        rows.append([f"P-{k:05d}", f"CG-{rng.randint(10000, 99999)}", f"C-{rng.randint(1, 1000):04d}",
                     rng.choice(["FULL", "FULL", "ASSIST"]), issued.isoformat(), expiry.isoformat(), status, hours, aid])
    # planted: training hours sentinel 0, first-aid date blank, active but expired, duplicate permit numbers
    zero = rng.sample(range(len(rows)), 22)
    for i in zero:
        rows[i][7] = 0
    blank = rng.sample([i for i in range(len(rows)) if i not in zero], 57)
    for i in blank:
        rows[i][8] = ""
    exp_rows = [i for i, r in enumerate(rows) if r[6] == "EXPIRED"]
    stale = rng.sample(exp_rows, 18)
    for i in stale:
        rows[i][6] = "ACTIVE"
    dup = rng.sample(range(len(rows)), 9)
    for i in dup:
        rows.append(list(rows[i]))
    write(FILES / "examples" / "permits.csv", ["permit_no", "caregiver_id", "centre_id", "permit_type", "issue_date",
                                               "expiry_date", "status", "training_hours", "first_aid_date"], rows)
    key.update({"rows": len(rows), "zero_hours": len(zero), "blank_first_aid": len(blank), "active_expired": len(stale), "duplicates": len(dup)})
    return key


def main() -> None:
    rng = random.Random(203)
    lab = licensing(rng)
    monthly_report(lab)
    rule_history(rng)
    field_sample(rng, lab)
    issue_log(lab)
    address_extract(lab)
    open_data(lab)
    ai_tabular(rng, lab)
    ai_documents()
    lab["key"]["permits_example"] = permits_example(rng)
    REF.mkdir(parents=True, exist_ok=True)
    (REF / "seeded_defects.json").write_text(json.dumps(lab["key"], ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline=chr(10))
    k = lab["key"]
    print("rows:", k["counts"])
    for name, v in k["defects"].items():
        print(f"{name:4} {v['table']:18} {v['column']:32} {v['rows']}")
    print("field sample wrong:", k["field_sample_wrong"], "of 60")


if __name__ == "__main__":
    main()
