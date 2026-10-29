"""Drift metrics: distance of a measured distribution from the exact rulebook distribution."""
import json

import numpy as np


def tvd(p: dict, q: dict) -> float:
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in set(p) | set(q))


def rmspe(measured: dict, exact: dict) -> float:
    """Borujeni's metric [B09]: root mean square percentage error of marginals, in %."""
    return 100 * float(np.sqrt(np.mean([((measured[k] - exact[k]) / exact[k]) ** 2 for k in exact])))


def normalise(counts: dict) -> dict:
    tot = sum(counts.values())
    return {k: v / tot for k, v in counts.items()}


def marginals(dist: dict, names, states) -> dict:
    """Per-node marginal {node: [p per state]} of a {combo: p} distribution."""
    out = {}
    for i, (nm, st) in enumerate(zip(names, states)):
        v = [0.0] * len(st)
        for combo, p in dist.items():
            v[combo[i]] += p
        out[nm] = v
    return out


def drift_entry(valid_counts: dict, n_invalid: int, shots: int, exact: dict, baseline_counts: dict,
                names, states, gate_info: dict) -> dict:
    """One variant x mode block of drift.json."""
    meas = normalise(valid_counts)
    base = normalise(baseline_counts)
    mm, me = marginals(meas, names, states), marginals(exact, names, states)
    return {
        "shots": shots,
        "invalid_shot_fraction": n_invalid / shots,
        "joint_tvd": tvd(meas, exact),
        "baseline_ancestral_tvd": tvd(base, exact),
        "marginal_tvd": {nm: 0.5 * sum(abs(a - b) for a, b in zip(mm[nm], me[nm])) for nm in names},
        "rmspe_marginals_pct": rmspe({f"{n}.{i}": v for n in names for i, v in enumerate(mm[n]) if me[n][i] > 0},
                                     {f"{n}.{i}": v for n in names for i, v in enumerate(me[n]) if v > 0}),
        **gate_info,
    }


def write(path, doc: dict):
    path.write_text(json.dumps(doc, indent=2, default=str) + "\n")
