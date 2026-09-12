#!/usr/bin/env python3
"""PJ0 -- germ/soma split (Weismann barrier): the first NEW biology in the QAL program.

A single-lineage germ/soma organism that fixes the exact wound P2 exposed: the faithful
damping model entangles the mortal phenotype to the immortal genotype (``cx(g,p)``) then
dissipates it, so body-death irreversibly decoheres the gene-witness (why the damping
ceiling collapsed to W* in [4,8)). PJ0 severs that coupling:

  * germ line (genotype) = the immortal GHZ chain that carries the entanglement witness,
    kept coherent -- built FULLY before any death (rung 0: pass the gene first).
  * soma (phenotype)     = the mortal trait, expressed as a SEPARABLE diagonal state
    (no cx(g,p) back-action; reuse the unitary arm's ry(aged)) then killed IN ISOLATION
    (rung 1) so its death is qubit-disjoint from the germ line and cannot touch the witness.
  * soma death is a PARAMETER (rung 2):
      - 'natural'       : T1 idle toward |0> (no operator, no bath); the aging clock is the
                          scheduler's idle pattern (driver: per-soma delay + selective DD on
                          the germ line only). Irregular lifespans are a lifelike FEATURE;
                          only the SCALE of that irregularity is gated (aging_order_deviation).
                          The acceptance gate (Q6). No bath -> leaner segment (2W).
      - 'local_damping' : the damping arm WITH the cx(g,p) removed and the bath scoped to the
                          phenotype -- controlled rate, reproducible; reference/fallback.
      - 'none'          : control arm (no death, age ignored) for Static Test 1.

The certified quantum claim stays the GENOTYPE-ONLY witness <X^W> (soma qubits are honestly
diagonal, excluded from the witness -- CD-3/CD-4).

CD-1 deviation (developer-directed, OQ-1): PJ0 is a SEPARATE experimental file pair
(``pj_qalife.py`` + ``pj_run_qalife.py``); the faithful reproduction (``qalife.py`` /
``run_qalife.py``) is left byte-stable. This file imports ``qalife`` READ-ONLY for pure
helpers (witness math, ``_z_geno_chain``, the physics constants); germ/soma build logic is
written fresh. The layout is organism-offset parameterized so PJ1 (arena) tiles adjacent
segments without a rewrite -- but PJ0 builds one organism (o=0) only (§3 out of scope).

Verification (CD-7, OQ-4): NO sim, NO hardware in this ticket. Correctness is proven by
STATIC circuit-structure evaluation -- ``--selftest`` (structural assertions incl. Static
Test 1) + ``--dump-circuit`` printing. The actual W sweeps are the developer's, later.

Usage:
    cd artificial-life/code
    python pj_qalife.py --selftest
    python pj_qalife.py --width 12 --steps 6 --dump-circuit
    python pj_qalife.py --width 4 --steps 4 --phenotype entangled --dump-circuit
"""

from __future__ import annotations

import argparse
import functools
import math
import os
from typing import Any

from qiskit import QuantumCircuit

import qalife as q4  # READ-ONLY: pure helpers + physics constants (Q1, no edits to qalife.py)

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))

# Physics constants are the faithful 2018 values -- reused, not redefined (CD-1 read-only).
AGING_DELTA = q4.AGING_DELTA      # per-time-step aging angle
DAMP_GAMMA = q4.DAMP_GAMMA        # per-time-step amplitude-damping probability (local_damping arm)
ALIVE_THRESH = q4.ALIVE_THRESH    # phenotype <sigma_z> >= this => at the |0> dark state => DEAD

# soma-death modes that attach a bath ancilla (extends the qubit segment by +W).
_BATH_MODES = ("local_damping",)


# ---------------------------------------------------------------------------
# Layout: SEPARATE germ / soma blocks, organism-offset parameterized (OQ-2 option B).
# One organism's span = germ (W) + soma (W) [+ bath (W) only in local_damping mode].
# geno block is CONTIGUOUS base..base+W-1 -> gene-passing clone is nearest-neighbor (the
# clean GHZ ladder the witness reads); soma block sits physically apart (I4 isolation).
# The organism index `o` is the PJ1 horizontal-scaling hook (PJ0 builds o=0 only).
# ---------------------------------------------------------------------------
def segment_len(width: int, has_bath: bool) -> int:
    """Qubit span of one organism: germ + soma [+ bath]."""
    return 2 * width + (width if has_bath else 0)


def organism_base(o: int, width: int, has_bath: bool) -> int:
    """First physical qubit of organism `o` (segments tile end-to-end -- PJ1 hook)."""
    return o * segment_len(width, has_bath)


def geno_q(o: int, k: int, width: int, has_bath: bool = False) -> int:
    """Germ-line (genotype) qubit for individual k of organism o -- contiguous block."""
    return organism_base(o, width, has_bath) + k


def pheno_q(o: int, k: int, width: int, has_bath: bool = False) -> int:
    """Soma (phenotype) qubit for individual k of organism o -- physically apart from germ."""
    return organism_base(o, width, has_bath) + width + k


def soma_bath_q(o: int, k: int, width: int, has_bath: bool = True) -> int:
    """Soma bath ancilla for individual k of organism o (local_damping mode only)."""
    return organism_base(o, width, has_bath) + 2 * width + k


def _bar(qc: QuantumCircuit, annotate: bool, label: str) -> None:
    """Labeled barrier for circuit analysis (--dump-circuit); no-op otherwise."""
    if annotate:
        try:
            qc.barrier(label=label)
        except TypeError:                        # older qiskit: barrier without label
            qc.barrier()


# ---------------------------------------------------------------------------
# The germ/soma model -- two-phase build (this IS rung 0, structurally).
# ---------------------------------------------------------------------------
def build_germsoma(width: int, steps: int, thetas: list[float], *,
                   phenotype: str = "separable", soma_death: str = "natural",
                   founder_equator: bool = True, delta: float = AGING_DELTA,
                   gamma: float = DAMP_GAMMA, organisms: int = 1,
                   annotate: bool = False) -> QuantumCircuit:
    """Single-lineage germ/soma organism after `steps` life-cycle steps.

    Two phases, in order:
      Phase 1 -- PASS THE GENE FIRST (rung 0): build the ENTIRE germ-line GHZ chain (founder
        + clones + mutations) before any soma gate. Clone cx is nearest-neighbor on the
        contiguous germ block.
      Phase 2 -- EXPRESS + KILL THE SOMA IN ISOLATION (rung 1): set the phenotype's diagonal
        <sigma_z> from the genotype value via ry(aged) (separable -- no cx(g,p) back-action),
        then apply a phenotype-only soma death. No gate couples a soma qubit to a germ qubit
        (Static Test 1) -- except the deliberate 'entangled' A/B mode which restores cx(g,p)
        to DEMONSTRATE it would cost the witness.

    phenotype   : 'separable' (default, the faithful diagonal soma) | 'entangled' (A/B: adds a
                  gratuitous cx(g,p) before the SAME ry(aged) angle).
    soma_death  : 'natural' (default, the acceptance gate -- T1 idle, no operator, no bath) |
                  'local_damping' (rigid reference -- damping arm sans cx(g,p), bath on the
                  phenotype) | 'none' (control -- no death, age ignored).
    organisms   : PJ0 builds 1 (o=0); the o-loop is the PJ1 arena hook (§3 out of scope).
    """
    if phenotype not in ("separable", "entangled"):
        raise ValueError(f"unknown phenotype {phenotype!r}")
    if soma_death not in ("natural", "local_damping", "none"):
        raise ValueError(f"unknown soma_death {soma_death!r}")

    has_bath = soma_death in _BATH_MODES
    n_data = organisms * segment_len(width, has_bath)
    qc = QuantumCircuit(n_data)

    z_geno = q4._z_geno_chain(width, thetas, founder_equator)

    # --- Phase 1: pass the gene first (germ line, fully, before any death) ---
    for o in range(organisms):
        for k in range(width):
            g = geno_q(o, k, width, has_bath)
            if k == 0:
                if founder_equator:
                    qc.ry(math.pi / 2, g)                 # FOUNDER (ancestral genotype, equator)
            else:
                qc.cx(geno_q(o, k - 1, width, has_bath), g)  # SELF-REPLICATION (nearest-neighbor)
            qc.ry(thetas[k], g)                            # MUTATION u3(theta,0,0) = Ry(theta)
    _bar(qc, annotate, "germline")
    # PJ1: resource qubit + boundary coherent-coupling (partial-SWAP) between neighbors here.

    # --- Phase 2: express + kill the soma, isolated (per organism, per individual) ---
    for o in range(organisms):
        for k in range(width):
            g = geno_q(o, k, width, has_bath)
            p = pheno_q(o, k, width, has_bath)
            age = max(0, steps - k)

            # separable-phenotype ry angle: <sigma_z> = genotype value, aged toward |0>.
            angle0 = math.acos(max(-1.0, min(1.0, z_geno[k])))
            aged = angle0 if soma_death == "none" else max(0.0, angle0 - delta * age)

            if phenotype == "entangled":
                qc.cx(g, p)                                # A/B: restores the wound (I7)
            qc.ry(aged, p)                                 # PHENOTYPE express (+ built-in aging)

            # SOMA DEATH -- phenotype qubit ONLY (never touches the germ line).
            if soma_death == "local_damping" and age > 0:
                bath = soma_bath_q(o, k, width, has_bath)
                g_eff = 1.0 - (1.0 - gamma) ** age
                qc.cry(2.0 * math.asin(math.sqrt(min(1.0, g_eff))), p, bath)
                qc.cx(bath, p)
            # 'natural': no operator -- death is T1 idle (driver: delay + selective DD on germ).
            # 'none'   : no operator -- control arm.
            _bar(qc, annotate, f"soma{o},{k}")

    return qc


def to_witness_basis(qc: QuantumCircuit, width: int, *, phenotype: str = "separable",
                     soma_death: str = "natural", organisms: int = 1) -> QuantumCircuit:
    """Rotate genotype qubits into the X basis (H then Z-read = witness). Separable soma stays
    in Z (diagonal -- excluded from the witness, CD-3). The 'entangled' A/B mode additionally
    H's the phenotypes (they carry half the GHZ). Returns a NEW circuit (does not mutate qc)."""
    has_bath = soma_death in _BATH_MODES
    out = qc.copy()
    for o in range(organisms):
        for k in range(width):
            out.h(geno_q(o, k, width, has_bath))
            if phenotype == "entangled":
                out.h(pheno_q(o, k, width, has_bath))
    return out


# ---------------------------------------------------------------------------
# Observables + static analysis (build-time only -- NO execution, OQ-4).
# ---------------------------------------------------------------------------
def witness_qubits(width: int, organisms: int = 1, has_bath: bool = False) -> list[int]:
    """Genotype-only qubit set for the witness <X^W> (CD-3). The soma is diagonal, excluded.
    PJ0: o=0. This is the set the developer's later runs feed to xbasis_witness_from_counts."""
    return [geno_q(o, k, width, has_bath) for o in range(organisms) for k in range(width)]


def soma_qubits(width: int, organisms: int = 1, has_bath: bool = False) -> list[int]:
    """All soma qubits (phenotype + bath) -- the mortal block, disjoint from the germ line."""
    out: list[int] = []
    for o in range(organisms):
        for k in range(width):
            out.append(pheno_q(o, k, width, has_bath))
            if has_bath:
                out.append(soma_bath_q(o, k, width, has_bath))
    return out


def soma_z_closed_form(width: int, steps: int, thetas: list[float], *,
                       soma_death: str = "natural", founder_equator: bool = True,
                       delta: float = AGING_DELTA) -> list[float]:
    """Separable soma <sigma_z> per individual (closed form): cos(aged), same as the unitary
    arm. Used by --selftest check (iv) and the A/B <sigma_z>-equality claim (AC-PJ0.4)."""
    z_geno = q4._z_geno_chain(width, thetas, founder_equator)
    out = []
    for k in range(width):
        age = max(0, steps - k)
        angle0 = math.acos(max(-1.0, min(1.0, z_geno[k])))
        aged = angle0 if soma_death == "none" else max(0.0, angle0 - delta * age)
        out.append(math.cos(aged))
    return out


def _qubit_index(qc: QuantumCircuit, bit: Any) -> int:
    """Physical qubit index of a bit, across qiskit versions."""
    return qc.find_bit(bit).index


def germsoma_coupling_report(qc: QuantumCircuit, width: int, *, organisms: int = 1,
                             has_bath: bool = False) -> dict[str, Any]:
    """STATIC circuit analyzer (walks qc.data; no statevector). Returns:
      * disjoint      : True iff NO gate mixes a germ qubit with a soma qubit (Static Test 1).
      * mixing_gates  : list of (name, [qubits]) offenders (empty when disjoint).
      * gene_first    : True iff every germ-block gate precedes every soma-touching gate.
      * witness_set   : the genotype-only witness qubit list.
      * gate_counts   : per-operator gate tally.
    Barriers are not couplings -- excluded from the disjointness/ordering checks."""
    germ = set(witness_qubits(width, organisms, has_bath))
    soma = set(soma_qubits(width, organisms, has_bath))

    mixing: list[tuple[str, list[int]]] = []
    gate_counts: dict[str, int] = {}
    last_germ_pos = -1
    first_soma_pos = None
    for pos, inst in enumerate(qc.data):
        name = inst.operation.name
        gate_counts[name] = gate_counts.get(name, 0) + 1
        if name in ("barrier", "delay"):
            continue
        qs = [_qubit_index(qc, b) for b in inst.qubits]
        touches_germ = any(q in germ for q in qs)
        touches_soma = any(q in soma for q in qs)
        if touches_germ and touches_soma:
            mixing.append((name, qs))
        if touches_germ and not touches_soma:
            last_germ_pos = pos
        if touches_soma and first_soma_pos is None:
            first_soma_pos = pos

    gene_first = (first_soma_pos is None) or (last_germ_pos < first_soma_pos)
    return {
        "disjoint": len(mixing) == 0,
        "mixing_gates": mixing,
        "gene_first": gene_first,
        "witness_set": witness_qubits(width, organisms, has_bath),
        "soma_set": sorted(soma),
        "gate_counts": gate_counts,
    }


def aging_order_deviation(scheduled_qc: QuantumCircuit, width: int,
                          organisms: int = 1, has_bath: bool = False) -> dict[str, Any]:
    """STATIC aging-clock analyzer (AC-PJ0.2). From a SCHEDULED circuit's per-soma idle
    (summed ``delay`` durations on each phenotype wire), rank somas by idle time and compare to
    their birth rank (individual k, oldest first). Returns per-soma shift + max_deviation, in
    GENERATIONS. Aging need NOT be monotone -- small irregularity is a lifelike feature; only
    max_deviation is gated (AGING_ORDER_TOL). No execution -- reads the scheduling analysis.

    Proxy note: idle is measured as summed Delay durations per phenotype qubit; on an unscheduled
    circuit (no delays) every idle is 0 -> deviation 0. The driver schedules before calling."""
    phenos = [pheno_q(o, k, width, has_bath) for o in range(organisms) for k in range(width)]
    idle = {q: 0.0 for q in phenos}
    for inst in scheduled_qc.data:
        if inst.operation.name != "delay":
            continue
        for b in inst.qubits:
            q = _qubit_index(scheduled_qc, b)
            if q in idle:
                dur = getattr(inst.operation, "duration", 0) or 0
                idle[q] += float(dur)

    # birth rank: individual k of each organism; oldest (largest age) = k=0 = rank 0.
    order = [(o, k) for o in range(organisms) for k in range(width)]
    birth_rank = {pheno_q(o, k, width, has_bath): i for i, (o, k) in enumerate(order)}
    # realized idle rank: most-idle (deadest) = rank 0.
    idle_sorted = sorted(phenos, key=lambda q: idle[q], reverse=True)
    idle_rank = {q: i for i, q in enumerate(idle_sorted)}

    per_soma = []
    max_dev = 0
    for i, (o, k) in enumerate(order):
        q = pheno_q(o, k, width, has_bath)
        shift = idle_rank[q] - birth_rank[q]
        max_dev = max(max_dev, abs(shift))
        per_soma.append({"organism": o, "individual": k, "qubit": q,
                         "birth_rank": birth_rank[q], "idle_rank": idle_rank[q],
                         "idle": idle[q], "shift": shift})
    return {"per_soma": per_soma, "max_deviation": max_dev}


# ---------------------------------------------------------------------------
# --selftest -- STATIC circuit-structure checks (CD-7 verification, no sim).
# ---------------------------------------------------------------------------
def _selftest_width(width: int, steps: int, seed: int) -> list[tuple[str, bool, str]]:
    """The five static checks at one width. Returns (name, ok, detail) per check."""
    thetas = q4._sim_thetas(width, seed, mut_scale=0.0)   # faithful 2018: clean GHZ (Q5)
    results: list[tuple[str, bool, str]] = []

    # (i) Static Test 1 -- geno/soma qubit-disjoint for every non-entangled soma_death mode.
    disjoint_all = True
    detail_i = []
    for mode in ("natural", "local_damping", "none"):
        has_bath = mode in _BATH_MODES
        qc = build_germsoma(width, steps, thetas, phenotype="separable", soma_death=mode)
        rep = germsoma_coupling_report(qc, width, has_bath=has_bath)
        disjoint_all = disjoint_all and rep["disjoint"]
        detail_i.append(f"{mode}={'disjoint' if rep['disjoint'] else 'MIXED'}")
    results.append(("Static Test 1 (geno/soma qubit-disjoint)", disjoint_all, ", ".join(detail_i)))

    # (ii) ordering (rung 0) -- gene fully passed before any soma gate.
    qc = build_germsoma(width, steps, thetas, soma_death="natural")
    rep = germsoma_coupling_report(qc, width, has_bath=False)
    results.append(("ordering: gene passed before any death (rung 0)", rep["gene_first"],
                    f"gene_first={rep['gene_first']}"))

    # (iii) witness readout isolation -- H on genotype qubits only (separable).
    meas = to_witness_basis(qc, width, phenotype="separable", soma_death="natural")
    germ = set(witness_qubits(width))
    soma = set(soma_qubits(width))
    h_geno = h_soma = 0
    for inst in meas.data:
        if inst.operation.name != "h":
            continue
        for b in inst.qubits:
            qi = _qubit_index(meas, b)
            h_geno += qi in germ
            h_soma += qi in soma
    ok_iii = (h_geno == width) and (h_soma == 0)
    results.append(("witness readout: H on genotype qubits only", ok_iii,
                    f"H(geno)={h_geno} H(soma)={h_soma}"))

    # (iv) separable <sigma_z> closed form -- soma ry angle == max(0, acos(z) - delta*age).
    z_expected = soma_z_closed_form(width, steps, thetas, soma_death="natural")
    qc_ry = build_germsoma(width, steps, thetas, soma_death="natural")
    ry_angles = _pheno_ry_angles(qc_ry, width)
    ok_iv = all(abs(math.cos(a) - z) < 1e-9 for a, z in zip(ry_angles, z_expected)) \
        and len(ry_angles) == width
    results.append(("separable <sigma_z> matches closed form (rung 1)", ok_iv,
                    f"max|cos(ry)-z|={_max_z_err(ry_angles, z_expected):.2e}"))

    # (v) entangled A/B contrast -- 'entangled' DOES contain cx(g,p) (fails (i)) but carries the
    #     SAME soma ry angle (so the entanglement is gratuitous).
    qc_e = build_germsoma(width, steps, thetas, phenotype="entangled", soma_death="natural")
    rep_e = germsoma_coupling_report(qc_e, width, has_bath=False)
    ry_e = _pheno_ry_angles(qc_e, width)
    same_angle = len(ry_e) == width and all(abs(a - b) < 1e-12 for a, b in zip(ry_e, ry_angles))
    ok_v = (not rep_e["disjoint"]) and same_angle
    results.append(("entangled A/B: cx(g,p) present, same ry angle (gratuitous)", ok_v,
                    f"disjoint={rep_e['disjoint']} same_ry_angle={same_angle}"))
    return results


def _pheno_ry_angles(qc: QuantumCircuit, width: int, has_bath: bool = False) -> list[float]:
    """The ry angle applied to each phenotype qubit p_0..p_{W-1} (organism 0), in k order."""
    want = {pheno_q(0, k, width, has_bath): k for k in range(width)}
    angles: dict[int, float] = {}
    for inst in qc.data:
        if inst.operation.name != "ry":
            continue
        qi = _qubit_index(qc, inst.qubits[0])
        if qi in want and qi not in angles:              # first ry on the phenotype = express angle
            angles[qi] = float(inst.operation.params[0])
    return [angles[q] for q in sorted(want, key=lambda q: want[q]) if q in angles]


def _max_z_err(ry_angles: list[float], z_expected: list[float]) -> float:
    if not ry_angles:
        return float("inf")
    return max(abs(math.cos(a) - z) for a, z in zip(ry_angles, z_expected))


def run_selftest(widths: tuple[int, ...] = (2, 4, 12), steps: int = 6, seed: int = 100) -> int:
    """Run the five static checks at representative widths. Print per-check OK, return 0/1."""
    print("=== PJ0 germ/soma --selftest (STATIC circuit-structure checks; no sim) ===")
    all_ok = True
    for w in widths:
        print(f"\n-- width W={w}, steps={steps} --")
        for name, ok, detail in _selftest_width(w, steps, seed):
            all_ok = all_ok and ok
            print(f"  [{'OK ' if ok else 'FAIL'}] {name}  ({detail})")
    print("\nSELFTEST PASS" if all_ok else "\nSELFTEST FAIL")
    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# Static-eval CLI (no sim, no run JSON) -- build, print, evaluate correctness.
# ---------------------------------------------------------------------------
def print_correctness_report(width: int, steps: int, thetas: list[float], *,
                             phenotype: str, soma_death: str) -> None:
    """Build the germ/soma circuit, print it + a gate->operator legend + the STATIC correctness
    report (Static Test 1, ordering, witness set, closed-form <sigma_z>). No execution."""
    has_bath = soma_death in _BATH_MODES
    qc = build_germsoma(width, steps, thetas, phenotype=phenotype, soma_death=soma_death,
                        annotate=True)
    rep = germsoma_coupling_report(qc, width, has_bath=has_bath)
    z_cf = soma_z_closed_form(width, steps, thetas, soma_death=soma_death)

    print(f"\n--- PJ0 GERM/SOMA CIRCUIT (W={width}, steps={steps}, "
          f"phenotype={phenotype}, soma_death={soma_death}) ---")
    base_g, base_p = geno_q(0, 0, width, has_bath), pheno_q(0, 0, width, has_bath)
    print(f"  layout (organism o=0, separate blocks): "
          f"germ g_k = {base_g}..{base_g + width - 1}  |  "
          f"soma p_k = {base_p}..{base_p + width - 1}"
          + (f"  |  bath = {soma_bath_q(0, 0, width, has_bath)}.."
             f"{soma_bath_q(0, width - 1, width, has_bath)}" if has_bath else "  |  (no bath)"))
    print("  gate -> Darwinian meaning:")
    print("    Ry(pi/2) on g_0        = FOUNDER  (ancestral genotype, equator)")
    print("    CX(g_{k-1} -> g_k)     = SELF-REPLICATION  (partial sigma_z clone, nearest-neighbor)")
    print("    Ry(theta_k) on g_k     = MUTATION")
    if phenotype == "entangled":
        print("    CX(g_k -> p_k)         = A/B WOUND  (gratuitous coupling -- costs the witness)")
    print("    Ry(aged) on p_k        = PHENOTYPE express (separable diagonal soma, +aging)")
    if soma_death == "local_damping":
        print("    CRY+CX(p_k, bath_k)    = SOMA DEATH  (local damping -> |0>; bath on phenotype only)")
    elif soma_death == "natural":
        print("    (no death operator)    = SOMA DEATH  (natural T1 idle; driver delay + selective DD)")
    else:
        print("    (no death operator)    = control arm  (no death, age ignored)")
    print("    H on g_k then measure  = witness readout (genotypes in X); soma stays diagonal")

    draw = qc.draw(output="text", fold=-1)
    print("\n" + str(draw))

    print("\n--- STATIC CORRECTNESS REPORT ---")
    print(f"  Static Test 1 (geno/soma qubit-disjoint): "
          f"{'YES' if rep['disjoint'] else 'NO'}"
          + ("" if rep["disjoint"] else f"  mixing gates: {rep['mixing_gates']}"))
    print(f"  gene passed before any death (rung 0):    {'YES' if rep['gene_first'] else 'NO'}")
    print(f"  witness qubit set (genotype only):        {rep['witness_set']}")
    print(f"  soma qubit set (excluded from witness):   {rep['soma_set']}")
    print(f"  gate counts:                              {rep['gate_counts']}")
    print("  separable soma <sigma_z> per individual (closed form):")
    print("    " + ", ".join(f"{z:+.3f}" for z in z_cf))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ0 germ/soma model (static evaluation; no sim, no hardware -- OQ-4).")
    ap.add_argument("--width", type=int, default=12, help="population width W (any W; 12 anchor)")
    ap.add_argument("--steps", type=int, default=6, help="life-cycle steps")
    ap.add_argument("--soma-death", dest="soma_death",
                    choices=["natural", "local_damping", "none"], default="natural",
                    help="natural (gate) | local_damping (reference) | none (control)")
    ap.add_argument("--phenotype", choices=["separable", "entangled"], default="separable",
                    help="separable (faithful) | entangled (A/B: gratuitous cx(g,p))")
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--selftest", action="store_true",
                    help="run the static circuit-structure checks and exit")
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print the annotated circuit + static correctness report")
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(run_selftest(steps=args.steps, seed=args.seed))

    thetas = q4._sim_thetas(args.width, args.seed, mut_scale=0.0)   # faithful (Q5)
    print_correctness_report(args.width, args.steps, thetas,
                             phenotype=args.phenotype, soma_death=args.soma_death)


if __name__ == "__main__":
    main()
