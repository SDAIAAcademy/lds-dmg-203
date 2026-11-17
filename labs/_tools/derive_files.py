"""Write the files that come from running the kit on the case data (after prepare_files.py).

    uv run _tools/derive_files.py

files/day2/run_log_reference.csv: the run of the 20 reference checks (lab 2.4 starts from it).
files/day2/draft_scorecard.csv: the reporting team's first scorecard, as it would be sent.
"""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
DAY2 = LABS / "files" / "day2"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out = LABS / "out" / "derive_run_log.csv"
    subprocess.run([sys.executable, str(LABS / "kit" / "run_checks.py"), str(LABS / "solutions" / "reference" / "checks_reference.yml"),
                    "--out", str(out)], check=True, capture_output=True)
    shutil.copyfile(out, DAY2 / "run_log_reference.csv")
    with out.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    checked = sum(int(r["rows_checked"]) for r in rows)
    failed = sum(int(r["rows_failed"]) for r in rows)
    by = defaultdict(list)
    for r in rows:
        by[r["dimension"]].append(float(r["pass_rate"]))
    lines = [["جودة بيانات الترخيص (الإجمالي)", f"{100 * (checked - failed) / checked:.1f}", "ممتاز", "أخضر"]]
    for dim, rates in sorted(by.items()):
        avg = sum(rates) / len(rates)
        lines.append([dim, f"{avg:.1f}", "ممتاز" if avg >= 95 else "جيد", "أخضر" if avg >= 95 else "أصفر"])
    with (DAY2 / "draft_scorecard.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["البند", "النسبة %", "التقدير", "اللون"])
        w.writerows(lines)
    out.unlink()
    print("\n".join(" | ".join(l) for l in lines))


if __name__ == "__main__":
    main()
