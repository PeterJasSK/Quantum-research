"""M4 checks, M5 t_doping, M8 certify and the R6 runner: the deep T-doped ring with ancilla checks (L2 attempt).

Stage-D reading (wording only, plan G8): ring = lineage skeleton, T gates = mutations, checks = integrity of the
lineage record. The certificate is about the device, never the tumour. L2 stays blocked until a certified run exists.

M4. An ancilla (prepared |+>, read in X) dangles from one ring qubit q and can apply CZ(ancilla, q) at any time slot,
i.e. insert Z_q(t) under its control; it then measures the product of its insertions. That product is deterministic
when, pulled back to slot 0, it is a stabilizer of |+>^n (X-type): over GF(2)

    sum over chosen (ancilla k, slot t) of zpart( backpropagate Z_{q_k} from t to 0 ) = 0.

One ancilla has depth + 1 unknowns against up to n constraints, so a single-ancilla check exists generically only
when depth + 1 > n (own observation, unverified: it would explain what depth 73 buys on a 64-ring, gap G1). At lean
depth the ancillas are grouped (size ceil((n + 1) / (depth + 1))) and the PARITY of a group's outcomes is the check.
The "web" R(t) of a check = its later insertions pulled back to slot t: a fault at (q, t) is detected iff it
anticommutes with R(t); a T gate at (q, t) keeps the check iff R(t) has I or Z on q. A solution of the GF(2)
system whose insertions multiply to +-i x stabilizer is not a check (it reads 50/50): `deterministic` drops it.

M5. T gates on random allowed sites (slots 0 .. depth - 1); fails loudly below the target.

M8. Direct fidelity estimation on the Clifford reference (t = 0): m random elements of the final stabilizer group,
each measured in its own Pauli basis, on accepted shots only (all checks satisfied). Bound = F - 1.645 sigma -
doping loss. The doping-loss term here is a PLACEHOLDER (a flat share of F), not the paper's Monte-Carlo term, and
the Pauli-noise assumption needs gate twirling that this runner does not add: the result is an attempt, not a
certificate.

Doped circuits are sampled on hardware only (36 to 76 qubits with T gates do not fit a local simulator); in
simulation the reference runs (stabilizer) and the doped circuits are built, counted and stored.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Pauli, StabilizerState

from common import qhard as QH, quantum as Q, runio
from common.runio import Ctx

TRIES = 200


# ---------------------------------------------------------------------------------------------- M4
def insertion_rows(sk: dict, q: int) -> np.ndarray:
    """Row t (0..depth): z-part at slot 0 of Z_q inserted at slot t."""
    n, depth = sk["n"], sk["depth"]
    rows = np.zeros((depth + 1, n), dtype=np.uint8)
    for t in range(depth + 1):
        x, z = np.zeros(n, dtype=np.uint8), np.zeros(n, dtype=np.uint8)
        z[q] = 1
        for tau in range(t, 0, -1):
            QH.backward_layer(sk, x, z, tau)
        rows[t] = z
    return rows


def web(sk: dict, ins: dict[int, list[int]], data_of: dict[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """R(t) for t = 0..depth as (x, z) arrays of shape (depth + 1, n). ins: {ancilla index: slots}."""
    n, depth = sk["n"], sk["depth"]
    wx, wz = np.zeros((depth + 1, n), dtype=np.uint8), np.zeros((depth + 1, n), dtype=np.uint8)
    x, z = np.zeros(n, dtype=np.uint8), np.zeros(n, dtype=np.uint8)
    for t in range(depth, -1, -1):
        wx[t], wz[t] = x, z
        for k, slots in ins.items():
            if t in slots:
                z[data_of[k]] ^= 1
        if t >= 1:
            QH.backward_layer(sk, x, z, t)
    if z.any():
        raise RuntimeError("check web does not close on an X-type stabilizer at slot 0 (construction bug)")
    return wx, wz


def deterministic(sk: dict, anc_data: list[int], ins: dict[int, list[int]]) -> bool:
    """The GF(2) condition of M4 fixes the check up to a phase: insertions that anticommute an odd number of times
    give a product +-i x stabilizer, which reads 50/50. True iff the ideal check parity is +-1."""
    n = sk["n"]
    anc = [{"ancilla": n + k, "data": q} for k, q in enumerate(anc_data)]
    st = StabilizerState(QH.circuit(sk, list(range(n)), anc, ins).remove_final_measurements(inplace=False))
    lab = ["I"] * (n + len(anc))
    for k in ins:
        lab[n + k] = "Z"
    return abs(abs(float(np.real(st.expectation_value(Pauli("".join(reversed(lab))))))) - 1) < 1e-9


def checks(sk: dict, anc_data: list[int], max_cz_per_anc: int, g: np.random.Generator) -> list[dict]:
    """M4. anc_data[k] = ring index of ancilla k's data qubit. -> [{ancillas, insertions {k: slots}, n_cz, wx, wz}]."""
    n, depth = sk["n"], sk["depth"]
    rows = [insertion_rows(sk, q) for q in anc_data]
    size = max(1, math.ceil((n + 1) / (depth + 1)))
    out, k0 = [], 0
    while k0 < len(anc_data):
        grp = list(range(k0, min(k0 + size, len(anc_data))))
        ker = QH.left_nullspace(np.concatenate([rows[k] for k in grp]))
        while len(ker) == 0 and grp[-1] + 1 < len(anc_data):
            grp.append(grp[-1] + 1)
            ker = QH.left_nullspace(np.concatenate([rows[k] for k in grp]))
        k0 = grp[-1] + 1
        if len(ker) == 0:
            continue
        best = None
        cands = [v for v in ker] + [np.bitwise_xor.reduce(ker[g.random(len(ker)) < 0.5], axis=0)
                                    for _ in range(TRIES) if len(ker) > 1]
        for c in cands:
            if c.ndim == 0 or not c.any():
                continue
            per = c.reshape(len(grp), depth + 1)
            cnt = per.sum(1)
            if (cnt == 0).any() or (cnt > max_cz_per_anc).any():
                continue
            ins = {grp[i]: [int(t) for t in np.flatnonzero(per[i])] for i in range(len(grp))}
            wx, wz = web(sk, ins, {k: anc_data[k] for k in grp})
            weight = int((wx | wz).sum())
            if (best is None or weight > best["weight"]) and deterministic(sk, anc_data, ins):
                best = {"ancillas": grp, "insertions": ins, "n_cz": int(cnt.sum()), "weight": weight, "wx": wx, "wz": wz}
        if best:
            out.append(best)
    return out


def allowed_t_sites(sk: dict, cks: list[dict]) -> list[tuple[int, int]]:
    """(ring index, slot) where a Z-type rotation commutes with every check; slots 0 .. depth - 1."""
    n, depth = sk["n"], sk["depth"]
    block = np.zeros((depth + 1, n), dtype=bool)
    for c in cks:
        block |= c["wx"].astype(bool)
    return [(int(q), int(t)) for t in range(depth) for q in range(n) if not block[t, q]]


def detected_fraction(sk: dict, cks: list[dict]) -> float:
    """Share of single-qubit Pauli faults (site, slot, X / Y / Z) that flip at least one check."""
    n, depth = sk["n"], sk["depth"]
    if not cks:
        return 0.0
    dx = np.zeros((depth + 1, n), bool)         # X fault: anticommutes with a web that has Z or Y there
    dz = np.zeros((depth + 1, n), bool)
    dy = np.zeros((depth + 1, n), bool)
    for c in cks:
        dx |= c["wz"].astype(bool)
        dz |= c["wx"].astype(bool)
        dy |= (c["wx"] ^ c["wz"]).astype(bool)
    return float((dx.sum() + dz.sum() + dy.sum()) / (3 * n * (depth + 1)))


# ---------------------------------------------------------------------------------------------- M5
def t_doping(sites: list[tuple[int, int]], t_target: int, g: np.random.Generator) -> list[tuple[int, int]]:
    """M5. Fails loudly when the checks leave fewer than t_target commuting sites (gap G2)."""
    if t_target == 0:
        return []
    if len(sites) < t_target:
        raise Q.Refused(f"T capacity {len(sites)} < target {t_target}: trade ancillas for T sites (gap G2)")
    idx = g.choice(len(sites), t_target, replace=False)
    return [sites[int(i)] for i in sorted(idx)]


# ---------------------------------------------------------------------------------------------- M8
DOPING_LOSS_SHARE = 0.10      # placeholder: share of the reference fidelity given up to doping (see certify)


def certify(values: list[float], sigmas: list[float], t: int) -> dict:
    """M8. values: sign-corrected stabilizer expectations of the Clifford reference.
    T gates are virtual Z rotations and add no noise; doping only turns "harmless" Clifford faults (accepted, and
    stabilizing the state) into harmful ones. 2607.25941 bounds that share by Monte Carlo over Pauli noise (about
    0.01 of 0.38 on their circuit). That simulation is not implemented: a flat share of F is subtracted instead."""
    v = np.array(values, float)
    F = float(v.mean())
    spread = float(v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else 0.0
    shot = float(math.sqrt((np.array(sigmas) ** 2).sum()) / len(v))
    sigma = max(spread, shot)
    loss = DOPING_LOSS_SHARE * max(F, 0.0) if t else 0.0
    return {"F_reference": F, "sigma": sigma, "m": len(v), "lb95_reference": F - 1.645 * sigma, "t": t,
            "doping_loss": loss, "bound": F - 1.645 * sigma - loss,
            "doping_loss_model": f"placeholder: {DOPING_LOSS_SHARE:.0%} of F; the Monte-Carlo harmless-fault bound of "
                                 f"2607.25941 is not implemented [verify]"}


# ---------------------------------------------------------------------------------------------- forecast from the ladder
SIGNAL_SIGMA = 3.0            # a ring is not run when its forecast reference fidelity is below this many sigma
ACCEPTED_SHARE = 0.07         # share of the gate loss left in the accepted shots (desk model of QH.acceptance_model)


def forecast(n: int, n_cz: int, m_dfe: int, shots: int, loss: dict | None) -> dict | None:
    """Distance to L2 from the loss meter of this run (R5-LADDER: lam per CZ, a per qubit). Desk model:
        accepted-shot fraction  exp(-lam N_CZ)
        fidelity of accepted    exp(-a n) exp(-ACCEPTED_SHARE lam N_CZ)
        sigma of the estimate   1 / sqrt(m_dfe shots accepted)
    lam_needed = the loss per CZ at which the signal is exactly SIGNAL_SIGMA. None without a ladder in the run.
    When D-DU ran in this run directory its loss per CZ layer (deep circuit, idle errors included) replaces the
    ladder's lam: a weight-2 operator crosses one to two CZ per layer, so it is used as the loss per CZ."""
    layer = (loss or {}).get("loss_per_layer")
    if not loss or (layer is None and loss.get("loss_per_cz") is None):
        return None
    lam = max(float(loss["loss_per_cz"] if layer is None else layer), 0.0)
    a = max(float(loss.get("readout_loss_per_qubit") or 0.0), 0.0)
    acc = math.exp(-lam * n_cz)
    fid = math.exp(-a * n - ACCEPTED_SHARE * lam * n_cz)
    signal = fid * math.sqrt(m_dfe * shots * acc)
    needed = (0.5 * math.log(m_dfe * shots) - a * n - math.log(SIGNAL_SIGMA)) / ((0.5 + ACCEPTED_SHARE) * n_cz)
    return {"n": n, "n_cz": int(n_cz), "m_dfe": m_dfe, "shots": shots, "loss_per_cz": lam, "readout_loss_per_qubit": a,
            "accepted_fraction": acc, "fidelity_accepted": fid, "signal_sigma": signal, "go": signal >= SIGNAL_SIGMA,
            "loss_per_cz_needed": needed, "label": loss.get("label") if layer is None else loss.get("layer_label"),
            "loss_source": "R5-LADDER loss per CZ" if layer is None else "D-DU loss per CZ layer",
            "rigour": "desk model on the loss meter's numbers"}


def l2_distance(run_dir, shots: int, config: str = "R6a-S36") -> dict | None:
    """What section H prints: the loss per CZ `config` needs against the one measured in this run. The CZ count is
    the ring's own (n depth / 2); its checks add more, so the real need is stricter."""
    from D_quantum_growth.main import CIRCUITS

    cfg = CIRCUITS[config]
    loss = runio.load_json(Path(run_dir) / "qhard" / "loss_per_cz.json")
    f = forecast(cfg["n"], cfg["n"] * cfg["depth"] // 2, cfg["m_dfe"], shots, loss)
    if f is None:
        return None
    return {"config": config, "needed": f["loss_per_cz_needed"], "measured": f["loss_per_cz"], "go": f["go"],
            "backend": f["label"], "note": f"ring CZ only (checks add more); desk model on the {f['loss_source']}"}


def _pauli_label(x: np.ndarray, z: np.ndarray) -> str:
    return "".join("IXZY"[int(a) + 2 * int(b)] for a, b in zip(x, z))


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    s = Q.session(ctx)
    tg = s.target
    n, depth = cfg["n"], cfg["depth"]
    lay = QH.ring_layout(tg, n, n_anc=cfg["n_anc"])
    ring, anc = lay["ring"], lay["ancillas"]
    pos = {q: k for k, q in enumerate(ring)}
    g = Q.rng(ctx, name, "ring")
    sk = QH.skeleton(n, depth, seed=int(g.integers(2 ** 31)))
    ent = QH.cut_entropy(sk, n_random=100)
    anc_data = [pos[a["data"]] for a in anc]
    cks = checks(sk, anc_data, max_cz_per_anc=cfg.get("max_cz_per_anc", 26), g=g)
    ins = {k: v for c in cks for k, v in c["insertions"].items()}
    sites = allowed_t_sites(sk, cks)
    while cks and len(sites) < max(cfg["t"]):                  # trade detection for T capacity (gap G2)
        cks.remove(max(cks, key=lambda c: int(c["wx"].sum())))
        ins = {k: v for c in cks for k, v in c["insertions"].items()}
        sites = allowed_t_sites(sk, cks)
    n_cz = QH.n_cz(sk) + sum(c["n_cz"] for c in cks)
    ledger = QH.classical_cost(sk, max(cfg["t"]))
    model = QH.acceptance_model(tg, ring, n_cz)
    lam = (runio.load_json(ctx.run_dir / "qhard" / "loss_per_cz.json") or {}).get("loss_per_cz")
    fc = forecast(n, n_cz, cfg["m_dfe"], ctx.shots, runio.load_json(ctx.run_dir / "qhard" / "loss_per_cz.json"))
    if fc is None:
        Q.log(f"{name}: no forecast (no R5-LADDER or D-DU in this run: qhard/loss_per_cz.json missing)")
    else:
        Q.log(f"{name}: forecast from the {fc['loss_source']} ({fc['label']}): accepted fraction {fc['accepted_fraction']:.2e}, "
              f"fidelity of accepted shots {fc['fidelity_accepted']:.3f}, signal {fc['signal_sigma']:.1f} sigma at "
              f"{cfg['m_dfe']} x {ctx.shots} shots; needs loss per CZ <= {fc['loss_per_cz_needed']:.4f}, measured "
              f"{fc['loss_per_cz']:.4f}")
        if not fc["go"]:
            raise Q.Refused(f"forecast signal {fc['signal_sigma']:.2f} sigma < {SIGNAL_SIGMA:.0f} at the shot budget: needs "
                            f"loss per CZ <= {fc['loss_per_cz_needed']:.4f}, measured {fc['loss_per_cz']:.4f}")
    design = {"forecast": fc,"ring": ring, "ancillas": anc, "depth": depth, "skeleton_seed": sk["seed"],
              "cut_entropy": ent, "classical_cost": ledger, "n_checks": len(cks),
              "checks": [{"ancillas": c["ancillas"], "n_cz": c["n_cz"], "web_weight": c["weight"]} for c in cks],
              "group_size": max(1, math.ceil((n + 1) / (depth + 1))), "first_order_detected": detected_fraction(sk, cks),
              "t_capacity": len(sites), "t_density_needed": max(cfg["t"]) / max(n * depth, 1), "n_cz_total": n_cz,
              "acceptance_model": model,
              "acceptance_from_ladder": math.exp(-lam * n_cz) if lam is not None else None, "layout": lay}
    Q.log(f"{name}: {n}-ring depth {depth}: min cut entropy {ent['min_half_arc']} (arc) / "
              f"{ent['min_random_bipartition']} (random); {len(cks)} checks from {len(anc)} ancillas, "
              f"{design['first_order_detected']:.0%} of first-order faults detected; T capacity {len(sites)}; "
              f"{n_cz} CZ; model acceptance {model['acceptance']:.2e}")

    # reference (t = 0): signs of the checks and of the DFE stabilizers from the ideal stabilizer state
    ref = QH.circuit(sk, ring, anc, ins, name="ref_z")
    st_full = StabilizerState(ref.remove_final_measurements(inplace=False))
    expect = []
    for c in cks:
        lab = ["I"] * (n + len(anc))
        for k in c["ancillas"]:
            lab[n + k] = "Z"
        ev = float(np.real(st_full.expectation_value(Pauli("".join(reversed(lab))))))
        if abs(abs(ev) - 1) > 1e-9:
            raise RuntimeError(f"check of ancillas {c['ancillas']} is not deterministic (expectation {ev})")
        expect.append(0 if ev > 0 else 1)
    st_data = StabilizerState(QH.circuit(sk, ring).remove_final_measurements(inplace=False))
    gx, gz = QH.stabilizers(sk)
    stabs = []
    for _ in range(cfg["m_dfe"]):
        c = g.integers(0, 2, n).astype(np.uint8)
        if not c.any():
            c[0] = 1
        x, z = (c @ gx) & 1, (c @ gz) & 1
        lab = _pauli_label(x, z)
        sign = float(np.real(st_data.expectation_value(Pauli(lab[::-1]))))
        stabs.append({"label": lab, "sign": 1 if sign > 0 else -1, "support": [int(j) for j in np.flatnonzero(x | z)]})
    circuits = [QH.circuit(sk, ring, anc, ins, basis=st["label"].replace("I", "Z"), name=f"dfe_{k:02d}")
                for k, st in enumerate(stabs)] + [ref]
    doped = {}
    for t in [v for v in cfg["t"] if v > 0]:
        tsites = t_doping(sites, t, g)
        qc = QH.circuit(sk, ring, anc, ins, t_sites=tsites, name=f"doped_t{t}")
        doped[t] = qc
        with open(ctx.path("qhard", name, f"doped_t{t}.qpy"), "wb") as f:
            qpy.dump(qc, f)
    if s.live:
        circuits += list(doped.values())
    bits, info = Q.execute(ctx, name, circuits, ctx.shots)
    design["info"] = info
    design["doped_circuits"] = {str(t): {"t_gates": t, "sampled": bool(s.live)} for t in doped}

    def accepted(bt: np.ndarray) -> np.ndarray:
        ok = np.ones(len(bt), dtype=bool)
        for c, e in zip(cks, expect):
            ok &= (bt[:, [n + k for k in c["ancillas"]]].sum(1) & 1) == e
        return ok

    vals, sigs, acc = [], [], []
    for st, bt in zip(stabs, bits[:len(stabs)]):
        ok = accepted(bt)
        acc.append(ok.mean())
        if ok.sum() == 0:
            continue
        v = st["sign"] * (1.0 - 2.0 * (bt[ok][:, st["support"]].sum(1) & 1))
        vals.append(float(v.mean()))
        sigs.append(float(math.sqrt(max(1 - v.mean() ** 2, 1e-12) / len(v))))
    acc_rate = float(np.mean(acc))
    t_max = max(cfg["t"])
    cert = certify(vals, sigs, t_max) if vals else None
    snap = bits[len(stabs)]
    snap_ok = snap[accepted(snap)][:, :n]
    seed_note = ring_seed_shapes(ctx, ring, snap_ok, name)
    result = design | {"acceptance_measured": acc_rate, "certificate": cert,
                       "accepted_reference_shots": int(sum(a * len(b) for a, b in zip(acc, bits))),
                       "seed_shapes": seed_note}
    if s.live:
        result["doped_acceptance"] = {str(t): float(accepted(bt).mean())
                                      for t, bt in zip(doped, bits[len(stabs) + 1:])}
    Q.save(ctx, name, result)
    if cert is None:
        return [Q.claim(ctx, name, cfg, None, None, False, info["label"], "no accepted reference shot: no certificate")]
    ok = cert["bound"] > 0 and (ledger["hard"] or "min_t" not in cfg)      # L2 circuits must be hard on the ledger
    if "min_entropy" in cfg:
        ok = ok and min(ent["min_half_arc"], ent["min_random_bipartition"]) >= cfg["min_entropy"]
    if "min_t" in cfg:
        ok = ok and t_max >= cfg["min_t"]
    return [Q.claim(ctx, name, cfg, cert["bound"], cert["sigma"], ok, info["label"],
                     f"F_ref {cert['F_reference']:.3f} on accepted shots (acceptance {acc_rate:.2e}, model "
                     f"{model['acceptance']:.2e}), m = {cert['m']}, placeholder doping loss {cert['doping_loss']:.3f} "
                     f"at t = {t_max}; min cut entropy {ent['min_half_arc']}; cheapest exact classical method "
                     f"{ledger['binding']} at 2^{ledger['log2_cost_min']:.0f} (threshold 2^{ledger['threshold_log2']}); {len(cks)} checks "
                     f"({design['first_order_detected']:.0%} first-order faults detected); doped circuits "
                     f"{'sampled' if s.live else 'built, not sampled (simulation)'}; certificate formula unverified, "
                     f"no agreement test against exact simulation here; {seed_note}")]


def ring_seed_shapes(ctx: Ctx, ring: list[int], shots_z: np.ndarray, name: str) -> str:
    """Seed shapes for section E: one accepted Z-snapshot of the ring per tumour, lifted to 3-D like D-SCALE's QCA
    snapshots. The snapshot is picked by rng(tile geometry seed), so a run replays the same seeds. Claim level per
    tile is L0: the ring's certificate attempt is run-level and about the device."""
    import networkx as nx

    from D_quantum_growth import seedlift as SL

    if len(shots_z) == 0:
        return "no seed shapes (no accepted shot)"
    n = len(ring)
    h = nx.Graph([(ring[k], ring[(k + 1) % n]) for k in range(n)])
    coords = {ring[k]: (math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)) for k in range(n)}
    patch = SL.patch_dict(h, coords, kind=f"ring{n}")
    masks, tiles = {}, {}
    for d in runio.draws(ctx.run_dir):
        shot = int(runio.rng(d["seed_hex"], "ring-snapshot").integers(len(shots_z)))
        active = [int(ring[k]) for k in np.flatnonzero(shots_z[shot])]
        masks[d["tile_id"]] = SL.lift(patch, active)
        tiles[d["tile_id"]] = {"region": f"ring{n}", "sites": n, "active": active, "shot": shot, "claim_level": "L0",
                               "seed_cells": int(masks[d["tile_id"]].sum()), "witness_passed": None}
    runio.save_seed_shapes(ctx, masks, tiles, name)
    return f"seed shapes for {len(masks)} tumours from accepted ring snapshots"
