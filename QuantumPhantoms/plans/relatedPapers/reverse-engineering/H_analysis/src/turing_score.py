"""Score a visual Turing test: accuracy, Clopper-Pearson 95 % CI, binomial test vs 0.5, 64-66 % benchmark.

    python -m H_analysis.src.turing_score answers.json key.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scipy import stats

BENCHMARK = (0.64, 0.66)  # Chuquicusma et al. [F08]


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else stats.beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def score(answers: list[dict], key: list[dict]) -> dict:
    truth = {k["id"]: k["truth"] for k in key}
    rows = [(a["call"] == truth[a["id"]], a["confidence"]) for a in answers]
    n, k = len(rows), sum(r[0] for r in rows)
    out = {"n": n, "correct": k, "accuracy": k / n, "ci95_clopper_pearson": clopper_pearson(k, n),
           "binomial_p_vs_0.5": float(stats.binomtest(k, n, 0.5).pvalue), "benchmark_accuracy": list(BENCHMARK),
           "vs_benchmark": "below" if k / n < BENCHMARK[0] else ("within" if k / n <= BENCHMARK[1] else "above"),
           "per_confidence": {}}
    for c in sorted({r[1] for r in rows}):
        sel = [r[0] for r in rows if r[1] == c]
        out["per_confidence"][c] = {"n": len(sel), "accuracy": sum(sel) / len(sel)}
    return out


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    ans = json.loads(Path(argv[0]).read_text())["answers"]
    key = json.loads(Path(argv[1]).read_text())
    r = score(ans, key)
    print(f"accuracy {r['accuracy']:.3f} ({r['correct']}/{r['n']}), 95% CI "
          f"[{r['ci95_clopper_pearson'][0]:.3f}, {r['ci95_clopper_pearson'][1]:.3f}], p vs 0.5 = {r['binomial_p_vs_0.5']:.3g}")
    print(f"benchmark {BENCHMARK[0]:.2f}-{BENCHMARK[1]:.2f} (F08): reader is {r['vs_benchmark']}; goal ~ 0.50")
    for c, v in r["per_confidence"].items():
        print(f"  confidence {c}: n={v['n']} accuracy={v['accuracy']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
