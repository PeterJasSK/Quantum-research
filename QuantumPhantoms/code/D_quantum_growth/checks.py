"""D-STC: a Clifford growth circuit with spacetime checks (plans/feature-QCAND-*.md). An own minimal check finder
after 2504.15725 [verify]; the published code was not inspected.

Payload   the Clifford ring of ring_l2.py (QH.skeleton) at several depths, no T gates.
Link      an ancilla (prepared |+>, read in X) next to ring qubit q applies a controlled Pauli P1 on q at slot t1
          and P2 on q at slot t2, where P2 = (layers t1+1 .. t2) P1 (the same layers)^-1. The two then cancel through
          the payload and the ancilla reads a fixed value. A fault between the two slots flips it iff it anticommutes
          with the link's Pauli at that slot (its "web"). Links are found by back-propagating X, Y and Z of q from
          every slot t2 (GF(2) propagation of common.qhard; the fixed value is read from qiskit's stabilizer
          simulation of the whole circuit): kept when the Pauli is again a single Pauli on q at an earlier slot, or
          when at slot 0 its Z part sits on q only (the rest is X-type and is absorbed by the |+> input, so the
          left end is a controlled Z or nothing).
Check     one ancilla = a chain of links with disjoint windows (most web weight first, at most `links` of them);
          two controlled Paulis that meet at one slot are merged into one. Its readout is the parity of its links.
Result    direct fidelity estimation on random elements of the final stabilizer group, on all shots of the checked
          circuit (F_raw: the check gates are in it) and on the shots where every check reads its value (F_kept).
          gain = F_kept / F_raw. No bound and no hardness claim: a measured gain on the road to L2.
"""
from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Pauli, StabilizerState

from common import qhard as QH, quantum as Q
from common.runio import Ctx

LINKS = 6                     # links per ancilla (each costs up to 2 two-qubit gates)


def links(sk: dict, q: int) -> list[dict]:
    """Every link of ring index q: {q, t1, t2, p1 (None = no left gate), p2, web {slot: (x, z)}, weight}. For each
    (t2, P2) the longest one."""
    n, out = sk["n"], []
    for t2 in range(1, sk["depth"] + 1):
        for p2 in "XYZ":
            x, z = np.zeros(n, dtype=np.uint8), np.zeros(n, dtype=np.uint8)
            x[q], z[q] = p2 in "XY", p2 in "YZ"
            web, best = {}, None
            for t in range(t2 - 1, -1, -1):
                QH.backward_layer(sk, x, z, t + 1)                       # the Pauli at slot t
                web[t] = (x.copy(), z.copy())
                if t == 0 and not np.delete(z, q).any():
                    best = (0, "Z" if z[q] else None)
                elif not np.delete(x | z, q).any():
                    best = (t, "IXZY"[int(x[q]) + 2 * int(z[q])])
            if best is not None:
                w = {t: web[t] for t in range(best[0], t2)}
                out.append({"q": q, "t1": best[0], "t2": t2, "p1": best[1], "p2": p2, "web": w,
                            "weight": int(sum((wx | wz).sum() for wx, wz in w.values()))})
    return out


def chain(cands: list[dict], depth: int, max_links: int, start: int = 0) -> list[dict]:
    """Links with disjoint windows and the largest summed web weight (interval scheduling), then the heaviest ones;
    among equals the ones nearest slot `start` (the ancillas' windows are staggered over the depth)."""
    best: list[tuple[int, list[dict]]] = [(0, [])]
    for t in range(1, depth + 1):
        cur = best[t - 1]
        for c in cands:
            if c["t2"] == t and best[c["t1"]][0] + c["weight"] > cur[0]:
                cur = (best[c["t1"]][0] + c["weight"], best[c["t1"]][1] + [c])
        best.append(cur)
    return sorted(sorted(best[depth][1], key=lambda c: (-c["weight"], abs(c["t1"] - start)))[:max_links],
                  key=lambda c: c["t1"])


def _anti(p: str, x: int, z: int) -> bool:
    return bool({"X": z, "Y": x ^ z, "Z": x}[p])


def _clash(a: dict, b: dict) -> bool:
    """A controlled Pauli of link a sits inside the window of link b and anticommutes with b's web there (the two
    ancillas would then be read as one entangled pair, not as two checks)."""
    for t, p in ((a["t1"], a["p1"]), (a["t2"], a["p2"])):
        if p and t in b["web"] and _anti(p, int(b["web"][t][0][a["q"]]), int(b["web"][t][1][a["q"]])):
            return True
    return False


def find(sk: dict, anc_data: list[int], max_links: int = LINKS) -> list[dict]:
    """One check per ancilla that has a link: [{ancilla (index into anc_data), q, links}]. Links that clash with a
    check taken earlier are left out."""
    out = []
    for k, q in enumerate(anc_data):
        taken = [ln for c in out for ln in c["links"]]
        ch = chain([ln for ln in links(sk, q) if not any(_clash(ln, o) or _clash(o, ln) for o in taken)],
                   sk["depth"], max_links, start=k * sk["depth"] // max(len(anc_data), 1))
        if ch:
            out.append({"ancilla": k, "q": q, "links": ch})
    return out


def detected_fraction(sk: dict, cks: list[dict]) -> float:
    """Share of single-qubit Pauli faults (site, slot, X / Y / Z) that flip at least one check."""
    n, depth = sk["n"], sk["depth"]
    hit = np.zeros((3, depth + 1, n), dtype=bool)
    for c in cks:
        for ln in c["links"]:
            for t, (wx, wz) in ln["web"].items():
                hit[0, t] |= wz.astype(bool)                                # an X fault anticommutes with Z or Y
                hit[1, t] |= (wx ^ wz).astype(bool)
                hit[2, t] |= wx.astype(bool)
    return float(hit.sum() / hit.size)


def _merge(ops: list[str]) -> tuple[list[str], str | None]:
    """Controlled Paulis of one ancilla on one qubit at one slot, in time order -> (phase gates on the ancilla, one
    controlled Pauli or None). P_b P_a = +-i P_c: the phase goes to the ancilla as S or S^dagger."""
    phases, cur = [], None
    for p in ops:
        if cur is None:
            cur = p
        elif cur == p:
            cur = None
        else:
            c = ({"X", "Y", "Z"} - {cur, p}).pop()
            phases.append("s" if (p + cur + c) in ("XYZ", "YZX", "ZXY") else "sdg")     # p . cur = +i c on a cycle
            cur = c
    return phases, cur


def payload(sk: dict, ring: list[int], anc: list[dict], cks: list[dict], basis: str | None = None,
            name: str = "stc", fault: tuple[str, int, int] | None = None) -> QuantumCircuit:
    """The ring circuit with its checks; check j uses circuit qubit n + j (physical anc[check ancilla]).
    fault = (Pauli, ring index, slot): one Pauli error put in by hand (manual verification)."""
    n = sk["n"]
    qc = QuantumCircuit(n + len(cks), n + len(cks), name=name)

    def slot_ops(t: int) -> None:
        for j, c in enumerate(cks):
            ops = [p for ln in c["links"] for tt, p in ((ln["t2"], ln["p2"]), (ln["t1"], ln["p1"])) if tt == t and p]
            phases, p = _merge(ops)
            for ph in phases:
                getattr(qc, ph)(n + j)
            if p:
                getattr(qc, {"X": "cx", "Y": "cy", "Z": "cz"}[p])(n + j, c["q"])
        if fault and fault[2] == t:
            getattr(qc, fault[0].lower())(fault[1])

    qc.h(range(n + len(cks)))
    slot_ops(0)
    for d in range(sk["depth"]):
        for q, gate in enumerate(sk["oneq"][d]):
            qc.sx(q)
            if gate == 1:
                qc.s(q)
        for i, j in sk["bonds"][d]:
            qc.cz(i, j)
        slot_ops(d + 1)
    for j, c in enumerate(cks):
        if c.get("y"):                                          # a link product of +-i x stabilizer: read in Y
            qc.sdg(n + j)
        qc.h(n + j)
    for q, p in enumerate(basis or "Z" * n):
        if p == "X":
            qc.h(q)
        elif p == "Y":
            qc.sdg(q)
            qc.h(q)
    qc.measure(range(n + len(cks)), range(n + len(cks)))
    qc.metadata = {"layout": [int(q) for q in ring] + [int(anc[c["ancilla"]]["ancilla"]) for c in cks]}
    return qc


def expected(sk: dict, cks: list[dict]) -> list[int]:
    """The value each check reads on the ideal circuit (stabilizer simulation). A check that reads 50/50 in X is
    switched to a Y readout (its links multiply to +-i x a stabilizer); one that still does is a construction bug."""
    n = sk["n"]
    anc = [{"ancilla": n + k} for k in range(max((c["ancilla"] for c in cks), default=-1) + 1)]

    def values() -> list[float]:
        st = StabilizerState(payload(sk, list(range(n)), anc, cks).remove_final_measurements(inplace=False))
        return [float(np.real(st.expectation_value(Pauli("I" * (len(cks) - 1 - j) + "Z" + "I" * (n + j)))))
                for j in range(len(cks))]

    ev = values()
    if any(abs(v) < 0.5 for v in ev):
        for c, v in zip(cks, ev):
            c["y"] = abs(v) < 0.5
        ev = values()
    if any(abs(abs(v) - 1) > 1e-9 for v in ev):
        raise RuntimeError(f"a check is not deterministic (expectations {ev})")
    return [0 if v > 0 else 1 for v in ev]


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    from scipy.stats import norm

    tg = Q.session(ctx).target
    n = cfg["n"]
    lay = QH.ring_layout(tg, n, n_anc=cfg["n_anc"])
    ring, anc = lay["ring"], lay["ancillas"]
    pos = {q: k for k, q in enumerate(ring)}
    g = Q.rng(ctx, name, "ring")
    plans, circuits = [], []
    for depth in cfg["depth"]:
        sk = QH.skeleton(n, depth, seed=int(g.integers(2 ** 31)))
        cks = find(sk, [pos[a["data"]] for a in anc], cfg.get("links", LINKS))
        st = StabilizerState(QH.circuit(sk, ring).remove_final_measurements(inplace=False))
        gx, gz = QH.stabilizers(sk)
        stabs = []
        for _ in range(cfg["m_dfe"]):
            c = g.integers(0, 2, n).astype(np.uint8)
            if not c.any():
                c[0] = 1
            x, z = (c @ gx) & 1, (c @ gz) & 1
            lab = "".join("IXZY"[int(a) + 2 * int(b)] for a, b in zip(x, z))
            sign = float(np.real(st.expectation_value(Pauli(lab[::-1]))))
            stabs.append({"label": lab, "sign": 1 if sign > 0 else -1, "support": [int(j) for j in np.flatnonzero(x | z)]})
        plans.append({"depth": depth, "sk": sk, "cks": cks, "expect": expected(sk, cks), "stabs": stabs,
                      "at": len(circuits)})
        circuits += [payload(sk, ring, anc, cks, basis=s["label"].replace("I", "Z"), name=f"stc_d{depth}_{k:02d}")
                     for k, s in enumerate(stabs)]
    bits, info = Q.execute(ctx, name, circuits, ctx.shots)
    rows = []
    for p in plans:
        sk, cks = p["sk"], p["cks"]
        vk, vr, d, var, kept = [], [], [], [], []
        for s, bt in zip(p["stabs"], bits[p["at"]:p["at"] + len(p["stabs"])]):
            ok = np.ones(len(bt), dtype=bool)
            for j, e in enumerate(p["expect"]):
                ok &= bt[:, n + j] == e
            v = s["sign"] * (1.0 - 2.0 * (bt[:, s["support"]].sum(1) & 1))
            kept.append(ok.mean())
            vr.append(v.mean())
            if ok.any() and not ok.all():                       # kept and rejected shots are disjoint samples
                f, a, b = ok.mean(), v[ok].mean(), v[~ok].mean()
                vk.append(a)
                d.append((1 - f) * (a - b))
                var.append((1 - f) ** 2 * ((1 - a * a) / ok.sum() + (1 - b * b) / (~ok).sum()))
            elif ok.all():
                vk.append(v.mean())
                d.append(0.0)
                var.append(0.0)
        row = {"depth": sk["depth"], "checks": len(cks), "links": sum(len(c["links"]) for c in cks),
               "spans": sorted({ln["t2"] - ln["t1"] for c in cks for ln in c["links"]}),
               "first_order_detected": detected_fraction(sk, cks),
               "n_cz": QH.n_cz(sk), "two_qubit_gates_max": info["two_qubit_gates_max"],
               "F_raw": float(np.mean(vr)), "kept_fraction": float(np.mean(kept))}
        if vk and row["F_raw"] > 0:
            sig = math.sqrt(sum(var)) / len(d) / row["F_raw"]
            row |= {"F_kept": float(np.mean(vk)), "gain": 1.0 + float(np.mean(d)) / row["F_raw"], "sigma_gain": max(sig, 1e-9)}
        else:
            row |= {"F_kept": None, "gain": None, "sigma_gain": None}
        rows.append(row)
    Q.save(ctx, name, {"ring": ring, "ancillas": anc, "layout": lay, "info": info, "rows": rows,
                       "note": "F_raw: all shots of the checked circuit (check gates included); F_kept: shots where "
                               "every check reads its value"})
    done = [r for r in rows if r["gain"] is not None]
    if not done:
        return [Q.claim(ctx, name, cfg, None, None, False, info["label"], "no check found or no usable shot: no gain")]
    z_need = 3.0 if len(done) == 1 else float(norm.isf(norm.sf(3.0) / len(done)))
    best = max(done, key=lambda r: (r["gain"] - 1) / r["sigma_gain"])
    ok = (best["gain"] - 1) / best["sigma_gain"] > z_need
    return [Q.claim(ctx, name, cfg, best["gain"], best["sigma_gain"], ok, info["label"],
                    "; ".join(f"depth {r['depth']}: gain {r['gain']:.3f} +- {r['sigma_gain']:.3f}, F {r['F_raw']:.3f} -> "
                              f"{r['F_kept']:.3f}, kept {r['kept_fraction']:.2f}, {r['checks']} checks ({r['links']} links, "
                              f"spans {r['spans']}), {r['first_order_detected']:.1%} of first-order faults detected"
                              for r in done)
                    + f"; {n}-ring; best depth shown, z > {z_need:.2f} needed; F_raw includes the check gates; own "
                      f"minimal finder (single-qubit ends on a dangling ancilla); no hardness claim")]
