"""M6 game_readout and the R5 runners: the stabilizer-submeasurement game on the cyclic cluster state.

Ring of n qubits in the cluster state (stabilizers K_j = Z_{j-1} X_j Z_{j+1}). Inputs sit on alternate sites:
bit 0 -> measure X, bit 1 -> measure Y; the other sites measure X. For a basis choice with Y-indicator y, a set S of
sites whose measured Paulis multiply to a stabilizer satisfies, over GF(2),

    s_{j-1} + s_{j+1} + y_j s_j = 0   for every j          (kernel of  A + diag(y))

so the deterministic parities of an input are exactly that kernel. An input is valid when the kernel is not trivial
(on the plain ring: the even-weight inputs). A shot wins when EVERY kernel generator has the right parity; the sign
of each generator comes from a stabilizer simulation of the ideal state. Requiring all generators is at least as
strict as any single-parity rule on the same inputs, so a classical bound for the published rule still bounds
classical players here, PROVIDED the published input set and basis rule are these [verify, 2110.04277 Sec. III, VI].

R5-Y18: two spacers of a 20-ring are always measured in Y, which contracts the ring to 18 players. The basis rule of
the four spacer neighbours (plain or X <-> Y swapped) is searched so that every even-weight 18-player input keeps a
deterministic parity; the spacer outcomes enter the parity (the byproduct sign fix). Refused if no rule works.

Scores are raw counts: no readout mitigation (plan X11).
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Pauli, StabilizerState

from common import qhard as QH, quantum as Q, runio
from common.runio import Ctx

MAX_ENUM_INPUTS = 12          # input sites enumerated exhaustively up to 2^12


def _ideal_state(n: int) -> StabilizerState:
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for i in range(0, n, 2):
        qc.cz(i, (i + 1) % n)
    for i in range(1, n, 2):
        qc.cz(i, (i + 1) % n)
    return StabilizerState(qc)


def _kernel(n: int, y: np.ndarray) -> np.ndarray:
    M = np.zeros((n, n), dtype=np.uint8)
    for j in range(n):
        M[j, (j - 1) % n] ^= 1
        M[j, (j + 1) % n] ^= 1
        M[j, j] ^= int(y[j])
    return QH.nullspace(M)


def build_game(n: int, spacers: int = 0) -> dict:
    """M6. -> {n, input_sites, rule: {site: (basis for bit 0, basis for bit 1)}, fixed: {site: basis}, spacers}."""
    if spacers not in (0, 2):
        raise ValueError("spacers: 0 (plain ring) or 2 (R5-Y18)")
    if spacers == 0:
        ins = list(range(0, n, 2))
        return {"n": n, "input_sites": ins, "rule": {j: ("X", "Y") for j in ins},
                "fixed": {j: "X" for j in range(1, n, 2)}, "spacers": []}
    sp = [0, n // 2]
    players = [j for j in range(n) if j not in sp]
    ins = players[0::2]
    nbrs = sorted({(p + d) % n for p in sp for d in (-1, 1)})
    best = None
    for swap in itertools.product((False, True), repeat=len(nbrs)):
        g = {"n": n, "input_sites": ins, "spacers": sp,
             "rule": {j: (("Y", "X") if j in nbrs and swap[nbrs.index(j)] else ("X", "Y")) for j in ins},
             "fixed": {j: ("Y" if j in nbrs and swap[nbrs.index(j)] else "X") for j in players if j not in ins}
             | {p: "Y" for p in sp}}
        ok = sum(1 for x in _all_inputs(len(ins)) if sum(x) % 2 == 0 and len(_kernel(n, _y(g, x))))
        if best is None or ok > best[0]:
            best = (ok, g, swap)
    need = 2 ** (len(ins) - 1)
    if best[0] < need:
        raise Q.Refused(f"R5-Y18: no spacer-neighbour basis rule keeps a deterministic parity for every even-weight "
                         f"input (best rule covers {best[0]} of {need}); gap G3 stays open")
    return best[1] | {"swap": {int(q): bool(s) for q, s in zip(nbrs, best[2])}}


def _all_inputs(k: int):
    return itertools.product((0, 1), repeat=k)


def bases(game: dict, x) -> str:
    out = [""] * game["n"]
    for j, b in game["fixed"].items():
        out[j] = b
    for j, bit in zip(game["input_sites"], x):
        out[j] = game["rule"][j][int(bit)]
    return "".join(out)


def _y(game: dict, x) -> np.ndarray:
    return np.array([c == "Y" for c in bases(game, x)], dtype=np.uint8)


def checks(game: dict, x, state: StabilizerState | None = None) -> list[dict]:
    """Deterministic parities of input x: [{"sites": [...], "parity": 0 | 1}]."""
    n = game["n"]
    state = state or _ideal_state(n)
    b = bases(game, x)
    out = []
    for s in _kernel(n, _y(game, x)):
        lab = ["I"] * n
        for j in np.flatnonzero(s):
            lab[int(j)] = b[int(j)]
        ev = float(np.real(state.expectation_value(Pauli("".join(reversed(lab))))))
        if abs(abs(ev) - 1) > 1e-9:
            raise RuntimeError(f"game check is not a stabilizer (expectation {ev}); construction bug")
        out.append({"sites": [int(j) for j in np.flatnonzero(s)], "parity": 0 if ev > 0 else 1})
    return out


def _valid(game: dict, x) -> bool:
    """Even-weight inputs only: an odd-weight input keeps just the input-independent parity of the fixed sites,
    which any classical player wins, so it would dilute the game."""
    return sum(x) % 2 == 0 and len(_kernel(game["n"], _y(game, x))) > 0


def pick_inputs(game: dict, how, g: np.random.Generator) -> list[tuple]:
    """how: "all" (every valid input) or a number (that many valid inputs, sampled without replacement)."""
    k = len(game["input_sites"])
    if k <= MAX_ENUM_INPUTS:
        valid = [x for x in _all_inputs(k) if _valid(game, x)]
        if how == "all" or int(how) >= len(valid):
            return valid
        return [valid[i] for i in sorted(g.choice(len(valid), int(how), replace=False))]
    out: set = set()
    want = 64 if how == "all" else int(how)
    for _ in range(200 * want):
        if len(out) >= want:
            break
        x = tuple(int(v) for v in g.integers(0, 2, k))
        if _valid(game, x):
            out.add(x)
    return sorted(out)


def merge(parts: list[QuantumCircuit], name: str) -> QuantumCircuit:
    """Disjoint tiles side by side: one circuit, one classical register, tile k at the offset of its qubits."""
    nq = sum(c.num_qubits for c in parts)
    qc = QuantumCircuit(nq, nq, name=name)
    lay, off = [], 0
    for c in parts:
        qc.compose(c, qubits=range(off, off + c.num_qubits), clbits=range(off, off + c.num_clbits), inplace=True)
        lay += list(c.metadata["layout"])
        off += c.num_qubits
    qc.metadata = {"layout": lay}
    return qc


def score(bits: np.ndarray, cks: list[dict]) -> np.ndarray:
    """Per-shot win flags: every deterministic parity holds."""
    win = np.ones(len(bits), dtype=bool)
    for c in cks:
        win &= (bits[:, c["sites"]].sum(1) & 1) == c["parity"]
    return win


def play(ctx: Ctx, key: str, rings: list[list[int]], game: dict, inputs: list[tuple], shots: int, pad: int = 0):
    """One job: one circuit per input, every ring in parallel. pad = identity pairs appended to the cluster circuit
    (one of its CZ layers applied twice; the loss ladder). -> (win rate per ring, sigma, per-input wins,
    per-input parities [{sites, parity, input_dependent, pass: rate per ring}], info)."""
    n = game["n"]
    sk = QH.skeleton(n, 2, cluster=True)
    for j in range(pad):
        sk["oneq"] += [[None] * n] * 2
        sk["bonds"] += [sk["bonds"][j % 2]] * 2
    sk |= {"depth": 2 + 2 * pad, "barrier": pad > 0}
    state = _ideal_state(n)
    circuits, cks = [], []
    for k, x in enumerate(inputs):
        b = bases(game, x)
        circuits.append(merge([QH.circuit(sk, r, basis=b, name=f"game_{k}") for r in rings], f"game_{k:03d}"))
        cks.append(checks(game, x, state))
    bits, info = Q.execute(ctx, key, circuits, shots)
    wins = np.zeros((len(rings), len(inputs)))
    parities = []
    for k, bt in enumerate(bits):
        for t in range(len(rings)):
            wins[t, k] = score(bt[:, t * n:(t + 1) * n], cks[k]).mean()
        parities.append([c | {"input_dependent": bool(set(c["sites"]) & set(game["input_sites"])),
                              "pass": [float(score(bt[:, t * n:(t + 1) * n], [c]).mean()) for t in range(len(rings))]}
                         for c in cks[k]])
    sh = info["shots"] if not isinstance(info["shots"], list) else info["shots"][0]
    sigma = np.sqrt((wins * (1 - wins)).sum(1) / max(sh, 1)) / len(inputs)
    return wins.mean(1), np.maximum(sigma, 1e-9), wins, parities, info


def _shots(ctx: Ctx, n_inputs: int) -> int:
    return max(100, min(ctx.shots, 8 * ctx.shots // max(n_inputs, 1)))


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    """R5-H12 / R5-MAP8 / R5-D20 / R5-Y18."""
    from scipy.stats import norm

    tg = Q.session(ctx).target
    n, tiles = cfg["n"], cfg.get("tiles", 1)
    if n == 12:
        lay = QH.tile_layout(tg, "hexagon", max_tiles=tiles)
        rings, relaxed = [t["qubits"] for t in lay], lay[0]["relaxed"]
    else:
        lay = QH.ring_layout(tg, n)
        rings, relaxed = [lay["ring"]], lay.get("relaxed", False)
    game = build_game(n, cfg.get("spacers", 0))
    inputs = pick_inputs(game, cfg["inputs"], Q.rng(ctx, name, "game-inputs"))
    win, sigma, per_input, parities, info = play(ctx, name, rings, game, inputs, _shots(ctx, len(inputs)))
    z = (win - cfg["bound"]) / sigma
    z_need = 3.0 if len(rings) == 1 else float(norm.isf(norm.sf(3.0) / len(rings)))       # Bonferroni over tiles
    ok = z > z_need
    need = cfg.get("min_pass", len(rings))
    Q.save(ctx, name, {"n": n, "rings": rings, "n_inputs": len(inputs), "inputs": inputs, "game": game, "info": info,
                       "win": win, "sigma": sigma, "z": z, "z_needed": z_need, "tiles_passed": int(ok.sum()),
                       "fidelity_estimate_2w_minus_1": 2 * win - 1, "win_per_input": per_input,
                       "parities_per_input": parities})
    k = int(np.argmax(win)) if len(rings) == 1 else int(np.argsort(win)[len(rings) // 2])
    rate = {dep: [p["pass"][k] for rows in parities for p in rows if p["input_dependent"] == dep] for dep in (True, False)}
    return [Q.claim(ctx, name, cfg, float(win[k]), float(sigma[k]), bool(ok.sum() >= need), info["label"],
                    f"{int(ok.sum())} of {len(rings)} rings pass (need {need}); n = {n}, {len(inputs)} inputs, raw counts"
                    + "; the value is the all-parities win rate; single parities on this ring: "
                    + ", ".join(f"{'input-dependent' if dep else 'input-independent'} {np.mean(v):.3f}"
                                for dep, v in rate.items() if v)
                    + " (which parity the published bound refers to: [verify])"
                    + ("; two Y-measured spacers" if game["spacers"] else "")
                    + ("; ring picked by measured error, calibration pruning skipped (it leaves no ring)" if relaxed else ""))]


def run_ladder(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    """R5-LADDER: rung (n, k) = the cluster ring of n qubits plus k identity pairs of its CZ layers (a layer applied
    twice), so N_CZ = n (1 + k). F from the game score (white-noise model: win = F + (1 - F) / 2^checks [verify]).
    Two-parameter least squares  -ln F = a n + lam N_CZ:  a = loss per qubit that does not grow with depth
    (preparation + readout), lam = loss per CZ. Written to <run>/qhard/loss_per_cz.json, where R6 reads both for its
    forecast. One job per rung."""
    tg = Q.session(ctx).target
    rows = []
    for n in cfg["n"]:
        try:
            ring = QH.ring_layout(tg, n)["ring"]
        except QH.NoLayout as e:
            rows.append({"n": n, "status": f"no layout: {e}"})
            continue
        game = build_game(n)
        inputs = pick_inputs(game, cfg["inputs"], Q.rng(ctx, name, f"ladder-inputs-{n}"))
        K = 2 ** len(checks(game, inputs[0]))                         # white noise wins with probability 1/K
        for k in cfg["k"]:
            win, sigma, _, _, info = play(ctx, f"{name}/n{n}k{k}", [ring], game, inputs, _shots(ctx, len(inputs)), pad=k)
            F = (K * float(win[0]) - 1) / (K - 1)
            rows.append({"n": n, "k": k, "status": "done", "win": float(win[0]), "sigma": float(sigma[0]), "F": F,
                         "sigma_F": K * float(sigma[0]) / (K - 1), "n_cz": n * (1 + k), "label": info["label"]})
    done = [r for r in rows if r.get("F", 0) > 0]
    if not done:
        Q.save(ctx, name, {"rows": rows, "status": "no usable rung"})
        return [Q.claim(ctx, name, cfg, None, None, False, "not run", "no ring gave a usable score")]
    X = np.array([[r["n"], r["n_cz"]] for r in done], float)
    y = np.array([-math.log(r["F"]) for r in done])
    sy = np.array([r["sigma_F"] / r["F"] for r in done])
    if np.linalg.matrix_rank(X) == 2:
        P = np.linalg.pinv(X)
        (a, lam), (sig_a, sig_lam) = P @ y, np.sqrt(np.diag(P @ np.diag(sy ** 2) @ P.T))
        fit = {"loss_per_cz": float(lam), "readout_loss_per_qubit": float(a), "sigma_lam": float(sig_lam),
               "sigma_a": float(sig_a)}
    else:                                                             # rungs on one line: gate and readout loss not separable
        x = X[:, 1]
        fit = {"loss_per_cz": float((x * y).sum() / (x * x).sum()), "readout_loss_per_qubit": None,
               "sigma_lam": float(math.sqrt(((x * sy) ** 2).sum()) / (x * x).sum()), "sigma_a": None}
    fit |= {"rungs": [[r["n"], r["k"]] for r in done], "source": name, "label": done[0]["label"],
            "model": "-ln F = a n + lam N_CZ, F from the white-noise reading of the game score [verify]"}
    Q.save(ctx, name, {"rows": rows} | fit)
    f = ctx.path("qhard", "loss_per_cz.json")                   # merged: D-DU's loss per layer stays when it ran first
    runio.save_json(f, (runio.load_json(f) or {}) | fit)
    a = fit["readout_loss_per_qubit"]
    return [Q.claim(ctx, name, cfg, fit["loss_per_cz"], fit["sigma_lam"], True, done[0]["label"],
                    f"{len(done)} rungs (n, k) = {', '.join(f'({r[0]}, {r[1]})' for r in fit['rungs'])}; loss per qubit "
                    + (f"outside the CZ layers a = {a:.4f} +- {fit['sigma_a']:.4f}" if a is not None else "not separated (one rung line)")
                    + "; a CZ layer applied twice can echo coherent errors, so lam may read low [verify]; shallow rungs "
                      "do not see the idle errors of a deep ring (gap G4)")]
