"""Reproduce the hash-chained, signed beacon pulse format offline + tamper demonstration. Target #5.

    python -m C_certificate.repro.beacon_chain

Verifies every cached NIST Beacon 2.0 pulse (signature, output hash, previous-output link,
precommitment), then flips one byte of one pulse in memory and shows where verification breaks.
Also reads the cached CURBy rounds (format sample) and compares their published protocol
parameters with Kavuri C04. Writes figures/beacon_chain.png.
"""
from __future__ import annotations

import copy

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from C_certificate.src.beacon import CHECKS, load_cache, verify_chain  # noqa: E402
from shared import RE_ROOT  # noqa: E402

FIG = RE_ROOT / "C_certificate" / "figures" / "beacon_chain.png"
KAVURI = {"nBitsOut": 512, "nBitsThreshold": 820}  # C04: 512-bit pulses from ≥ 820 bits of smooth min-entropy


def _grid(results: list[dict]) -> np.ndarray:
    """rows = checks, cols = pulses; 1 ok, 0 fail, 0.5 not applicable."""
    return np.array([[0.5 if r[c] is None else float(r[c]) for r in results] for c in CHECKS])


def main() -> None:
    cache = load_cache()
    clean = verify_chain(cache)
    n_links = sum(1 for r in clean if r["prev_link"] is not None)
    if all(r["ok"] for r in clean):
        print(f"chain OK ({n_links} links, {len(clean)} pulses {clean[0]['pulse_id']} … {clean[-1]['pulse_id']})")
    else:
        print("chain FAILED:", [r["pulse_id"] for r in clean if not r["ok"]])

    k = len(cache["pulses"]) // 2
    tampered = copy.deepcopy(cache)
    v = tampered["pulses"][k]["localRandomValue"]
    tampered["pulses"][k]["localRandomValue"] = f"{int(v[:2], 16) ^ 0x01:02X}" + v[2:]
    bad = verify_chain(tampered)
    print(f"tamper: flipped 1 bit of localRandomValue in pulse #{k} ({bad[k]['pulse_id']})")
    for r in bad:
        if not r["ok"]:
            print(f"  fails at #{r['index']} {r['pulse_id']}: " + ", ".join(c for c in CHECKS if r[c] is False))

    rounds = cache.get("curby_sample", {}).get("rounds", [])
    for rd in rounds:
        c = rd["data"]["content"]
        par = c.get("payload", {}).get("parameters", {})
        print(f"CURBy block index {c['index']} stage {c['payload'].get('stage')} round {c['payload'].get('round')} "
              f"{c['payload'].get('timestamp')}: nBitsOut {par.get('nBitsOut')} (paper {KAVURI['nBitsOut']}), "
              f"nBitsThreshold {par.get('nBitsThreshold')} (paper {KAVURI['nBitsThreshold']}), "
              f"isQuantum {par.get('isQuantum')}, {len(c.get('links', []))} links")
    for prev, rd in zip(rounds, rounds[1:]):
        links = [ln["/"] for ln in rd["data"]["content"].get("links", [])]
        print(f"CURBy block {rd['data']['content']['index']} links to previous CID: {prev['cid']['/'] in links} "
              "(reference only; CID not recomputed, dag-cbor not installed)")

    fig, axes = plt.subplots(2, 1, figsize=(7, 3.6), dpi=130, sharex=True)
    for ax, res, title in ((axes[0], clean, "cached chain"), (axes[1], bad, f"one bit flipped in pulse #{k}")):
        ax.imshow(_grid(res), cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
        ax.set_yticks(range(len(CHECKS)), CHECKS, fontsize=7)
        ax.set_title(title, fontsize=8)
    axes[1].set_xticks(range(len(clean)), [str(r["index"]) for r in clean], fontsize=7)
    axes[1].set_xlabel(f"pulse (NIST Beacon 2.0 chain {cache['chain_index']}); green = verifies")
    fig.tight_layout()
    fig.savefig(FIG)
    print(f"figure → {FIG.relative_to(RE_ROOT)}")


if __name__ == "__main__":
    main()
