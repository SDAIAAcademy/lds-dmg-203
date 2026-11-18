"""Estimate a defect rate from a random sample, with a 95% interval (Wilson score).

    uv run kit/sample_estimate.py --n 60 --failed 5 --population 1000

Use it when checking every row costs too much (a site visit per record). The interval is wide
for small samples: say it, do not report the point estimate alone.
"""
from __future__ import annotations

import argparse
import math


def wilson(failed: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = failed / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def pct(x: float) -> str:
    """A share as a percentage with one decimal, halves rounded up (5 of 80 is 6.3%, as on paper)."""
    return f"{math.floor(1000 * x + 0.5) / 10:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--failed", type=int, required=True)
    ap.add_argument("--population", type=int)
    a = ap.parse_args()
    lo, hi = wilson(a.failed, a.n)
    p = a.failed / a.n
    print(f"sample: {a.failed} of {a.n} failed = {pct(p)}")
    print(f"95% interval: {pct(lo)} to {pct(hi)}")
    if a.population:
        print(f"in {a.population} records: about {round(p * a.population)} (between {math.floor(lo * a.population)} and {math.ceil(hi * a.population)})")


if __name__ == "__main__":
    main()
