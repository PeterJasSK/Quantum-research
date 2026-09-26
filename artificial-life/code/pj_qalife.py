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


# ===========================================================================
# PJ1 -- THE ARENA: two germ/soma organisms colliding in one environment.
#
# Built ALONGSIDE PJ0 (build_germsoma untouched, organisms=1 path byte-stable). The arena
# uses a DIFFERENT physical layout than PJ0's segment_len: each organism = a contiguous germ
# block (W, the clean GHZ genealogy carrying the witness -- unchanged discipline) + a UNARY
# body track (`track` sites, one excitation = the body's location -- OQ-1) + `traits` idle
# qubits (the rung-5 reproduction/energy hook, built as nothing here, §3).
#
# The bodies are quantum walkers on a shared track (nearest-neighbor rxx+ryy hopping,
# excitation-conserving). Where the two bodies overlap, a coherent XX+YY exchange transfers
# excitation and entangles them -- interaction EMERGES from co-location (a Hamiltonian term at
# the shared sites), never `if(contact)` (AC-PJ1.4). Three arms:
#   * 'none'        -- walk only, no collision layer (control / product null; pass_through).
#   * 'soma_soma'   -- XX+YY exchange between the two BODY registers only; germ lines untouched
#                      -> the joint genealogy witness survives the collision (the result, I1).
#   * 'germ_routed' -- the SAME exchange routed through a GERM qubit -> joint witness collapses
#                      (the cross-organism Weismann kill-switch; deliberately breaks Static Test 1).
# ===========================================================================

# Fixed coupling defaults: (theta_walk, phi_collision). The driver sim-scans phi (I1a); these
# are the build-time defaults for --dump-circuit / --selftest structural checks.
DEFAULT_COUPLING = (0.6, math.pi / 2)


# ---------------------------------------------------------------------------
# Arena layout: germ block (W) + unary body track (`track`) + traits, organism-tiled.
# germ_q(o,*) contiguous -> nearest-neighbor clone (the clean witness ladder); body_q(o,*)
# unary (one-hot position); trait_q(o,*) idle. Segments tile end-to-end (I9: adjacent).
# ---------------------------------------------------------------------------
def arena_segment_len(width: int, track: int, traits: int) -> int:
    """Qubit span of one arena organism: germ (W) + unary body track + traits."""
    return width + track + traits


def arena_base(o: int, width: int, track: int, traits: int) -> int:
    """First physical qubit of arena organism `o` (adjacent segments -- I9)."""
    return o * arena_segment_len(width, track, traits)


def germ_q(o: int, k: int, width: int, track: int, traits: int) -> int:
    """Germ-line (genotype) qubit k of organism o -- contiguous block (clean GHZ genealogy)."""
    return arena_base(o, width, track, traits) + k


def body_q(o: int, j: int, width: int, track: int, traits: int) -> int:
    """Body (soma) unary track site j of organism o -- one excitation = the body's location."""
    return arena_base(o, width, track, traits) + width + j


def trait_q(o: int, t: int, width: int, track: int, traits: int) -> int:
    """Trait qubit t of organism o -- reproduction/energy hook (rung-5; built idle here, §3)."""
    return arena_base(o, width, track, traits) + width + track + t


def _walk_layer(qc: QuantumCircuit, width: int, organisms: int, track: int, traits: int,
                theta: float) -> None:
    """One nearest-neighbor XX+YY hop layer on each organism's unary body track (an
    excitation-conserving quantum walk -- the bodies move). Germ qubits untouched."""
    for o in range(organisms):
        for j in range(track - 1):
            a = body_q(o, j, width, track, traits)
            b = body_q(o, j + 1, width, track, traits)
            qc.rxx(theta, a, b)
            qc.ryy(theta, a, b)


def _collision_layer(qc: QuantumCircuit, width: int, organisms: int, track: int, traits: int,
                     interaction: str, phi: float, coll_site: int | None) -> None:
    """The coherent collision. `soma_soma`: XX+YY exchange between the two BODIES at aligned
    shared sites (body-body only -- germ never touched); it only acts where both bodies have
    amplitude, so contact emerges from co-location (no `if(contact)`). `germ_routed`: the SAME
    exchange routed through germ_q(1,0) (the cross-organism wound -- kills the joint witness)."""
    if interaction == "none":
        return
    if organisms < 2:                                # a collision needs two bodies
        return
    if interaction == "soma_soma":
        sites = range(track) if coll_site is None else [coll_site]
        for j in sites:
            a = body_q(0, j, width, track, traits)
            b = body_q(1, j, width, track, traits)
            qc.rxx(phi, a, b)
            qc.ryy(phi, a, b)
    elif interaction == "germ_routed":
        j = track // 2 if coll_site is None else coll_site
        a = body_q(0, j, width, track, traits)
        g = germ_q(1, 0, width, track, traits)       # route the exchange through a GERM qubit
        qc.rxx(phi, a, g)
        qc.ryy(phi, a, g)
    else:
        raise ValueError(f"unknown interaction {interaction!r}")


def build_arena(width: int, steps: int, thetas: list[float], *, organisms: int = 2,
                track: int = 6, traits: int = 1, interaction: str = "soma_soma",
                frame: int | None = None, founder_equator: bool = True,
                delta: float = AGING_DELTA, coupling: tuple[float, float] = DEFAULT_COUPLING,
                coll_site: int | None = None, annotate: bool = False) -> QuantumCircuit:
    """Two germ/soma organisms on a shared arena, evolved `frame` walk+collision layers.

    Phased build (rung-0 discipline preserved):
      1. GERM LINES FIRST: per organism, founder ry(pi/2) + nearest-neighbor cx clone chain +
         ry(thetas[k]) mutation on the contiguous germ block (clean GHZ; no death, no bath).
      2. BODIES: initialize each walker localized at opposite ends of the shared track.
      3. TIME EVOLUTION: repeat `frame` times a walk_layer (NN XX+YY hop on each body) then a
         collision_layer (the interaction). `frame` is the animation clock.

    `steps` is accepted for API parity with build_germsoma but does not drive the arena germ
    (clean GHZ ignores steps, exactly as PJ0's germ phase does); `frame` is the arena clock.
    No death channel, no bath -- all witness loss is real hardware noise (EM-fightable, CD-8).
    """
    if interaction not in ("none", "soma_soma", "germ_routed"):
        raise ValueError(f"unknown interaction {interaction!r}")
    theta, phi = coupling
    n_data = organisms * arena_segment_len(width, track, traits)
    qc = QuantumCircuit(n_data)

    # --- Phase 1: germ lines first (clean GHZ genealogy per organism) ---
    for o in range(organisms):
        for k in range(width):
            g = germ_q(o, k, width, track, traits)
            if k == 0:
                if founder_equator:
                    qc.ry(math.pi / 2, g)                          # FOUNDER (ancestral genotype)
            else:
                qc.cx(germ_q(o, k - 1, width, track, traits), g)   # SELF-REPLICATION (NN clone)
            qc.ry(thetas[k], g)                                    # MUTATION
    _bar(qc, annotate, "germline")

    # --- Phase 2: place the bodies at opposite ends of the shared track ---
    for o in range(organisms):
        start = 0 if o % 2 == 0 else track - 1
        qc.x(body_q(o, start, width, track, traits))               # unary: one excitation = body
        # PJ1-rung5: gated clone on trait_q(o, *) here (reproduction hook; built as nothing, §3).
    _bar(qc, annotate, "bodies")

    # --- Phase 3: time evolution -- walk + collision, `frame` times (the animation clock) ---
    n_layers = 0 if frame is None else int(frame)
    for f in range(n_layers):
        _walk_layer(qc, width, organisms, track, traits, theta)
        _collision_layer(qc, width, organisms, track, traits, interaction, phi, coll_site)
        _bar(qc, annotate, f"frame{f + 1}")

    return qc


def arena_to_witness_basis(qc: QuantumCircuit, width: int, *, organisms: int = 2,
                           track: int = 6, traits: int = 1) -> QuantumCircuit:
    """Rotate germ qubits of BOTH organisms into the X basis (H then Z-read = joint witness).
    Bodies stay in Z (unary occupancy -- diagonal, CD-3). Returns a NEW circuit."""
    out = qc.copy()
    for q in arena_witness_qubits(width, organisms, track, traits):
        out.h(q)
    return out


# ---------------------------------------------------------------------------
# Arena observables + static analysis (build-time only -- NO execution).
# ---------------------------------------------------------------------------
def arena_witness_qubits(width: int, organisms: int = 2, track: int = 6,
                         traits: int = 1) -> list[int]:
    """All germ qubits across both organisms -- the JOINT witness <X^{2W}> set (CD-3)."""
    return [germ_q(o, k, width, track, traits)
            for o in range(organisms) for k in range(width)]


def bipartite_cut_qubits(width: int, organisms: int = 2, track: int = 6,
                         traits: int = 1) -> tuple[list[int], list[int]]:
    """The A|B germ cut for the bipartite-cut witness (I1b): (organism-0 germ, organism-1 germ).
    For organisms>2 the cut is {o=0} | {o>=1} (only L=2 is built/run in PJ1, §3)."""
    a = [germ_q(0, k, width, track, traits) for k in range(width)]
    b = [germ_q(o, k, width, track, traits)
         for o in range(1, organisms) for k in range(width)]
    return a, b


def body_site_qubits(o: int, width: int, track: int, traits: int) -> list[int]:
    """Organism o's body track qubits -- the Z-basis occupancy readout set."""
    return [body_q(o, j, width, track, traits) for j in range(track)]


def arena_coupling_report(qc: QuantumCircuit, width: int, *, organisms: int = 2,
                          track: int = 6, traits: int = 1) -> dict[str, Any]:
    """STATIC arena analyzer (walks qc.data; no statevector). Returns:
      * per_organism_disjoint : {o: True iff NO gate couples org o's body to ANY germ qubit}
                                (per-organism Static Test 1).
      * all_disjoint          : True iff every organism is body/germ disjoint.
      * germ_coupled          : True iff any gate couples a body qubit to a germ qubit
                                (the germ_routed flag -- expected False for soma_soma/none).
      * has_classical_branch  : True iff any measurement-conditioned gate / measure / reset is
                                present on the body path (must be False -- AC-PJ1.4 no if(contact)).
      * mixing_gates          : list of (name, [qubits]) body/germ offenders.
      * witness_set           : the joint witness qubit list.
      * gate_counts           : per-operator gate tally.
    Barriers/delays are not couplings -- excluded from the disjointness checks."""
    germ = set(arena_witness_qubits(width, organisms, track, traits))
    body_by_o = {o: set(body_site_qubits(o, width, track, traits)) for o in range(organisms)}

    per_org_mixing: dict[int, list[tuple[str, list[int]]]] = {o: [] for o in range(organisms)}
    mixing: list[tuple[str, list[int]]] = []
    germ_coupled = False
    has_classical_branch = False
    gate_counts: dict[str, int] = {}
    for inst in qc.data:
        name = inst.operation.name
        gate_counts[name] = gate_counts.get(name, 0) + 1
        cond = getattr(inst.operation, "condition", None) or getattr(inst, "condition", None)
        if cond is not None or name in ("measure", "reset"):
            has_classical_branch = True
        if name in ("barrier", "delay"):
            continue
        qs = [_qubit_index(qc, b) for b in inst.qubits]
        touches_germ = any(q in germ for q in qs)
        if not touches_germ:
            continue
        for o in range(organisms):
            if any(q in body_by_o[o] for q in qs):
                per_org_mixing[o].append((name, qs))
                germ_coupled = True
                mixing.append((name, qs))

    per_organism_disjoint = {o: len(per_org_mixing[o]) == 0 for o in range(organisms)}
    return {
        "per_organism_disjoint": per_organism_disjoint,
        "all_disjoint": all(per_organism_disjoint.values()),
        "germ_coupled": germ_coupled,
        "has_classical_branch": has_classical_branch,
        "mixing_gates": mixing,
        "witness_set": arena_witness_qubits(width, organisms, track, traits),
        "gate_counts": gate_counts,
    }


# ---------------------------------------------------------------------------
# Arena --selftest -- five STATIC circuit-structure checks (CD-7, no sim).
# ---------------------------------------------------------------------------
def _arena_selftest_width(width: int, track: int, *, organisms: int = 2, traits: int = 1,
                          frame: int = 3, seed: int = 100) -> list[tuple[str, bool, str]]:
    """The five arena static checks at one (W, track). Returns (name, ok, detail) per check."""
    thetas = q4._sim_thetas(width, seed, mut_scale=0.0)   # faithful clean GHZ
    kw = dict(organisms=organisms, track=track, traits=traits)
    results: list[tuple[str, bool, str]] = []

    def _build(interaction: str) -> QuantumCircuit:
        return build_arena(width, 0, thetas, interaction=interaction, frame=frame, **kw)

    # (i) per-organism Static Test 1: holds for soma_soma/none, FAILS for germ_routed.
    rep_ss = arena_coupling_report(_build("soma_soma"), width, **kw)
    rep_no = arena_coupling_report(_build("none"), width, **kw)
    rep_gr = arena_coupling_report(_build("germ_routed"), width, **kw)
    ok_i = rep_ss["all_disjoint"] and rep_no["all_disjoint"] and (not rep_gr["all_disjoint"])
    results.append(("Static Test 1 per organism (soma_soma/none disjoint; germ_routed MIXED)",
                    ok_i, f"soma_soma={rep_ss['all_disjoint']} none={rep_no['all_disjoint']} "
                    f"germ_routed_disjoint={rep_gr['all_disjoint']}"))

    # (ii) germ-first ordering: no germ gate after any body/collision gate.
    qc_ss = _build("soma_soma")
    germ = set(arena_witness_qubits(width, **kw))
    body = {q for o in range(organisms) for q in body_site_qubits(o, width, track, traits)}
    last_germ = -1
    first_body = None
    for pos, inst in enumerate(qc_ss.data):
        if inst.operation.name in ("barrier", "delay"):
            continue
        qs = [_qubit_index(qc_ss, b) for b in inst.qubits]
        tg, tb = any(q in germ for q in qs), any(q in body for q in qs)
        if tg and not tb:
            last_germ = pos
        if tb and first_body is None:
            first_body = pos
    gene_first = (first_body is None) or (last_germ < first_body)
    results.append(("ordering: germ lines built before any body gate (rung 0)",
                    gene_first, f"gene_first={gene_first}"))

    # (iii) witness readout isolation: H on germ qubits of BOTH organisms only, bodies in Z.
    meas = arena_to_witness_basis(qc_ss, width, **kw)
    h_germ = h_body = 0
    for inst in meas.data:
        if inst.operation.name != "h":
            continue
        for b in inst.qubits:
            qi = _qubit_index(meas, b)
            h_germ += qi in germ
            h_body += qi in body
    ok_iii = (h_germ == organisms * width) and (h_body == 0)
    results.append(("witness readout: H on both germ lines only (bodies stay Z)",
                    ok_iii, f"H(germ)={h_germ} H(body)={h_body}"))

    # (iv) no classical branch on the body path (AC-PJ1.4: emergent, not if(contact)).
    ok_iv = (not rep_ss["has_classical_branch"]) and (not rep_no["has_classical_branch"])
    results.append(("no classical branch on contact (fully unitary collision)",
                    ok_iv, f"soma_soma_branch={rep_ss['has_classical_branch']} "
                    f"none_branch={rep_no['has_classical_branch']}"))

    # (v) pass_through == soma_soma minus the collision layer (structural diff): identical build
    #     except soma_soma carries exactly `frame * 2 * track` extra collision rxx+ryy gates.
    n_ss = rep_ss["gate_counts"].get("rxx", 0) + rep_ss["gate_counts"].get("ryy", 0)
    n_no = rep_no["gate_counts"].get("rxx", 0) + rep_no["gate_counts"].get("ryy", 0)
    expected_collision = frame * 2 * track                # 2 gates (xx+yy) per aligned site/frame
    other_ss = {k: v for k, v in rep_ss["gate_counts"].items() if k not in ("rxx", "ryy")}
    other_no = {k: v for k, v in rep_no["gate_counts"].items() if k not in ("rxx", "ryy")}
    ok_v = (n_ss - n_no == expected_collision) and (other_ss == other_no)
    results.append(("pass_through == soma_soma minus collision layer (structural diff)",
                    ok_v, f"extra_xxyy={n_ss - n_no} expected={expected_collision} "
                    f"non_collision_gates_equal={other_ss == other_no}"))
    return results


def run_arena_selftest(cases: tuple[tuple[int, int], ...] = ((2, 5), (4, 5), (12, 7)),
                       frame: int = 3) -> int:
    """Run the five arena checks at representative (W, track). Print per-check OK, return 0/1."""
    print("=== PJ1 arena --selftest (STATIC circuit-structure checks; no sim) ===")
    all_ok = True
    for w, track in cases:
        print(f"\n-- arena W={w}, track={track}, organisms=2, frame={frame} --")
        for name, ok, detail in _arena_selftest_width(w, track, frame=frame):
            all_ok = all_ok and ok
            print(f"  [{'OK ' if ok else 'FAIL'}] {name}  ({detail})")
    print("\nSELFTEST PASS" if all_ok else "\nSELFTEST FAIL")
    return 0 if all_ok else 1


def print_arena_report(width: int, steps: int, thetas: list[float], *, organisms: int,
                       track: int, traits: int, interaction: str, frame: int) -> None:
    """Build the arena circuit, print it + a legend + the STATIC arena correctness report."""
    qc = build_arena(width, steps, thetas, organisms=organisms, track=track, traits=traits,
                     interaction=interaction, frame=frame, annotate=True)
    rep = arena_coupling_report(qc, width, organisms=organisms, track=track, traits=traits)

    print(f"\n--- PJ1 ARENA CIRCUIT (W={width}, track={track}, organisms={organisms}, "
          f"interaction={interaction}, frame={frame}) ---")
    for o in range(organisms):
        g0 = germ_q(o, 0, width, track, traits)
        b0 = body_q(o, 0, width, track, traits)
        t0 = trait_q(o, 0, width, track, traits)
        print(f"  organism {o}: germ g_k = {g0}..{g0 + width - 1}  |  "
              f"body track = {b0}..{b0 + track - 1}  |  traits = {t0}..{t0 + traits - 1}")
    print("  gate -> meaning:")
    print("    Ry(pi/2)/CX/Ry(theta) on germ = FOUNDER / SELF-REPLICATION / MUTATION (clean GHZ)")
    print("    X on body site               = place the walker (unary: one excitation = body)")
    print("    RXX+RYY on NN body sites     = quantum walk hop (excitation-conserving)")
    if interaction == "soma_soma":
        print("    RXX+RYY across aligned bodies = COLLISION (body-body exchange; germ untouched)")
    elif interaction == "germ_routed":
        print("    RXX+RYY body<->germ_q(1,0)   = COLLISION routed through a GERM qubit (kill-switch)")
    else:
        print("    (no collision layer)         = control arm (walk only; product null)")
    print("    H on germ then measure        = joint witness readout; bodies stay diagonal (Z)")

    print("\n" + str(qc.draw(output="text", fold=-1)))

    print("\n--- STATIC ARENA CORRECTNESS REPORT ---")
    print(f"  per-organism Static Test 1 (body/germ disjoint): {rep['per_organism_disjoint']}")
    print(f"  all organisms disjoint:                          {rep['all_disjoint']}")
    print(f"  any body<->germ coupling (germ_routed flag):     {rep['germ_coupled']}")
    print(f"  classical branch on body path (must be False):   {rep['has_classical_branch']}")
    if rep["mixing_gates"]:
        print(f"  body/germ mixing gates:                          {rep['mixing_gates']}")
    a_cut, b_cut = bipartite_cut_qubits(width, organisms, track, traits)
    print(f"  joint witness set (both germ lines):             {rep['witness_set']}")
    print(f"  A|B bipartite cut (I1b):                         A={a_cut}  B={b_cut}")
    print(f"  gate counts:                                     {rep['gate_counts']}")


# ===========================================================================
# PJ2 -- THE SOLO VIVARIUM: one enriched proto-viral organism living in a habitat.
#
# Built ALONGSIDE PJ0/PJ1 (build_germsoma / build_arena untouched, byte-stable). A SINGLE
# organism whose genome has two co-inherited parts -- the WITNESS LOCI (the W-generation GHZ
# germ line carrying <X^W>, the quantum certified heredity) and a small register of CLASSICAL
# GENES (diagonal trait bits: role/repl/life). The soma BODY is a unary walker on a habitat
# lattice seeded with food; it FORAGES, EATS on co-location, STARVES if unfed, and BUDS when fed
# -- survival of the fittest EMERGES from one fixed local "vivarium Hamiltonian" H_viv, never a
# scripted cull. All in ONE circuit (time = depth; measured once). Grounded in the 2018 paper's
# Discussion "Scope of Quantum Artificial Life" (more DoF in genotype/phenotype; spatial
# variables; trace-out of dead units; error correction only in the genotype qubits).
#
# The Weismann barrier here is ASYMMETRIC (faithfulness -- not two disjoint things):
#   * germ->soma EXPRESSION is present  -- the body is built from the classical genes (a
#     diagonal gene->body gate); the paper's gene->body info is classical (encoded in <sigma_z>).
#   * soma->germ BACK-ACTION is forbidden -- no coherent gate couples a WITNESS LOCUS to the
#     mortal body (that would decohere the certified heredity). --gate-repl breaks it to MEASURE
#     the cost; germ_coupled is the A/B kill-switch.
# Only the witness loci carry the quantum claim; body/food/energy/genes are diagonal narrative.
# ===========================================================================

# Fixed vivarium laws (build-time defaults for --dump-circuit / --selftest structural checks).
VIV_FOOD_SITES = (2, 4)              # lattice feeding stations (always WIRED; seeded unless barren)
VIV_HOP = 0.6                        # H_forage: NN quantum-walk hop angle
VIV_STARVE = 0.6                     # H_starve: per-step decay of the body toward |0> (unfed death)
VIV_TRAITS = 3                       # classical genes: role(motility), repl, life
GENE_ROLE, GENE_REPL, GENE_LIFE = 0, 1, 2


# ---------------------------------------------------------------------------
# Vivarium layout: one organism, contiguous. witness germ (W) | genes | body track | food
# lattice | energy accumulator [| fitness ancilla only under hard_select].
# ---------------------------------------------------------------------------
def viv_food_sites(track: int, food_sites: tuple[int, ...] = VIV_FOOD_SITES) -> tuple[int, ...]:
    """Feeding-station sites clamped to the track (always wired; seeded unless barren)."""
    return tuple(s for s in food_sites if 0 <= s < track)


def viv_segment_len(width: int, track: int, traits: int, n_food: int, *,
                    hard_select: bool = False) -> int:
    """Qubit span: witness germ + genes + body + food lattice + energy + death bath + (fitness)."""
    return width + traits + 3 * track + n_food + (1 if hard_select else 0)


def viv_witness_q(k: int, width: int, track: int, traits: int) -> int:
    """Witness locus k -- the GHZ germ line (the quantum certified heredity)."""
    return k


def viv_gene_q(t: int, width: int, track: int, traits: int) -> int:
    """Classical gene t (role/repl/life) -- read to express the body (germ->soma)."""
    return width + t


def viv_body_q(j: int, width: int, track: int, traits: int) -> int:
    """Body unary track site j -- one excitation = the body's location."""
    return width + traits + j


def viv_food_q(j: int, width: int, track: int, traits: int) -> int:
    """Habitat food lattice site j (seeded |1> at the feeding stations unless barren)."""
    return width + traits + track + j


def viv_energy_q(i: int, width: int, track: int, traits: int) -> int:
    """Energy accumulator slot i (one per feeding station) -- 'ate at station i'."""
    return width + traits + 2 * track + i


def viv_bath_q(j: int, width: int, track: int, traits: int, n_food: int) -> int:
    """Death bath ancilla for body site j (amplitude-damps the unfed body toward |0>; traced out)."""
    return width + traits + 2 * track + n_food + j


def viv_fit_q(width: int, track: int, traits: int, n_food: int) -> int:
    """Static fitness ancilla (only under --hard-select)."""
    return width + traits + 3 * track + n_food


# ---------------------------------------------------------------------------
# The vivarium model -- one circuit: germ + genome/expression + Trotterized H_viv.
# ---------------------------------------------------------------------------
def build_vivarium(width: int, steps: int, thetas: list[float], *, track: int = 6,
                   traits: int = VIV_TRAITS, interaction: str = "vivarium",
                   food_sites: tuple[int, ...] = VIV_FOOD_SITES, hop: float = VIV_HOP,
                   starve: float = VIV_STARVE, founder_equator: bool = True,
                   role_on: bool = True, hard_select: bool = False, gate_repl: bool = False,
                   annotate: bool = False) -> QuantumCircuit:
    """One enriched proto-viral organism after `steps` life-cycle steps, in ONE circuit.

    interaction : 'vivarium'     -- habitat seeded with food; the emergent life cycle (result).
                  'barren'       -- SAME circuit law, NO food seeded (control; nothing to eat).
                  'germ_coupled' -- vivarium + a coherent body<->witness-locus gate (A/B: breaks
                                    the soma->germ ban -> the witness collapses).
    Phases: (1) germ line first (witness GHZ); (2) genome + germ->soma expression; (3) Trotterized
    H_viv = forage + eat + starve + bud, `steps` times (barrier per step = the sim snapshot);
    (4) germ_coupled back-action, if the arm; (5) static fitness comparator, if --hard-select.
    """
    if interaction not in ("vivarium", "barren", "germ_coupled"):
        raise ValueError(f"unknown interaction {interaction!r}")
    from qiskit.circuit.library import RXXGate, RYYGate

    sites = viv_food_sites(track, food_sites)
    n_food = len(sites)
    seed_food = interaction != "barren"
    kw = dict(width=width, track=track, traits=traits)
    n_data = viv_segment_len(width, track, traits, n_food, hard_select=hard_select)
    qc = QuantumCircuit(n_data)
    z_geno = q4._z_geno_chain(width, thetas, founder_equator)   # parity with PJ0 (unused metric)
    _ = z_geno

    # --- Phase 1: germ line first (witness GHZ genealogy) ---
    for k in range(width):
        g = viv_witness_q(k, **kw)
        if k == 0:
            if founder_equator:
                qc.ry(math.pi / 2, g)                              # FOUNDER
        else:
            qc.cx(viv_witness_q(k - 1, **kw), g)                   # SELF-REPLICATION (NN clone)
        qc.ry(thetas[k], g)                                        # MUTATION
    _bar(qc, annotate, "germline")

    # --- Phase 2: genome + germ->soma EXPRESSION (the body is built from the genes) ---
    for t, on in ((GENE_ROLE, role_on), (GENE_REPL, True), (GENE_LIFE, True)):
        if on and t < traits:
            qc.x(viv_gene_q(t, **kw))                              # set the classical genome
    # EXPRESSION: the body exists because the role gene says so (gene->soma, diagonal control).
    qc.cx(viv_gene_q(GENE_ROLE, **kw), viv_body_q(0, **kw))
    if seed_food:
        for s in sites:
            qc.x(viv_food_q(s, **kw))                              # habitat resources
    _bar(qc, annotate, "genome+habitat")

    hop_eff = hop if role_on else 0.0                             # genotype-encoded motility

    # --- Phase 3: Trotterized H_viv (emergent behavior; barrier per step = sim snapshot) ---
    for f in range(int(steps)):
        # H_forage: NN quantum-walk hop (conserving), + one energy-controlled hop (state-dependent).
        for j in range(track - 1):
            a, b = viv_body_q(j, **kw), viv_body_q(j + 1, **kw)
            qc.rxx(hop_eff, a, b)
            qc.ryy(hop_eff, a, b)
        if n_food:                                                 # fed body forages a little extra
            a, b = viv_body_q(0, **kw), viv_body_q(1, **kw)
            qc.append(RXXGate(hop_eff).control(1),
                      [viv_energy_q(0, **kw), a, b])
            qc.append(RYYGate(hop_eff).control(1),
                      [viv_energy_q(0, **kw), a, b])
        # H_eat: emergent consumption -- fires only where body AND food coincide (co-location).
        for i, s in enumerate(sites):
            qc.ccx(viv_body_q(s, **kw), viv_food_q(s, **kw), viv_energy_q(i, **kw))
            qc.cx(viv_energy_q(i, **kw), viv_food_q(s, **kw))      # consume the food
        # H_bud: a fed body seeds a neighbor (reproduction powered by having eaten).
        for i, s in enumerate(sites):
            if s + 1 < track:
                qc.ccx(viv_energy_q(i, **kw), viv_body_q(s, **kw), viv_body_q(s + 1, **kw))
        _bar(qc, annotate, f"step{f + 1}")

    # --- H_starve / trace-out death: every body ages toward |0> via a bath (aging), then the FED
    #     are revived -- survival of the fittest EMERGES (unfed stay dead). Soma-side only; witness
    #     untouched. Amplitude damping = the paper's dissipation, sim-visible + EM-fightable on HW.
    g_eff = min(1.0, max(0.0, starve))
    for j in range(track):
        bath = viv_bath_q(j, width=width, track=track, traits=traits, n_food=n_food)
        qc.cry(2.0 * math.asin(math.sqrt(g_eff)), viv_body_q(j, **kw), bath)
        qc.cx(bath, viv_body_q(j, **kw))                          # amplitude damp body -> |0> (death)
    for i, s in enumerate(sites):
        qc.cx(viv_energy_q(i, **kw), viv_body_q(s, **kw))         # REVIVE the fed (fittest survive)
    _bar(qc, annotate, "death+revive")

    # --- Phase 4: germ_coupled A/B -- a coherent body<->witness-locus gate (breaks the ban) ---
    if interaction == "germ_coupled" or gate_repl:
        j = track // 2
        qc.rxx(math.pi / 2, viv_body_q(j, **kw), viv_witness_q(0, **kw))
        qc.ryy(math.pi / 2, viv_body_q(j, **kw), viv_witness_q(0, **kw))
        _bar(qc, annotate, "germ_coupled" if interaction == "germ_coupled" else "gate_repl")

    # --- Phase 5: optional static fitness comparator (--hard-select; diagonal, no measurement) ---
    if hard_select and n_food:
        fit = viv_fit_q(width, track, traits, n_food)
        qc.mcx([viv_energy_q(i, **kw) for i in range(n_food)], fit)   # fit iff ate at all stations
        _bar(qc, annotate, "hard_select")

    return qc


def viv_to_witness_basis(qc: QuantumCircuit, width: int, *, track: int = 6,
                         traits: int = VIV_TRAITS) -> QuantumCircuit:
    """Rotate the witness loci into the X basis (H then Z-read). Body/food/energy/genes stay in Z
    (diagonal -- excluded from the witness, CD-3). Returns a NEW circuit."""
    out = qc.copy()
    for q in viv_witness_qubits(width, track=track, traits=traits):
        out.h(q)
    return out


# ---------------------------------------------------------------------------
# Vivarium observables + static analysis (build-time only -- NO execution).
# ---------------------------------------------------------------------------
def viv_witness_qubits(width: int, track: int = 6, traits: int = VIV_TRAITS) -> list[int]:
    """The witness loci -- the germ line, the <X^W> set (CD-3)."""
    return [viv_witness_q(k, width, track, traits) for k in range(width)]


def viv_gene_qubits(width: int, track: int = 6, traits: int = VIV_TRAITS) -> list[int]:
    return [viv_gene_q(t, width, track, traits) for t in range(traits)]


def viv_body_site_qubits(width: int, track: int = 6, traits: int = VIV_TRAITS) -> list[int]:
    return [viv_body_q(j, width, track, traits) for j in range(track)]


def viv_food_qubits(width: int, track: int = 6, traits: int = VIV_TRAITS) -> list[int]:
    return [viv_food_q(j, width, track, traits) for j in range(track)]


def viv_energy_qubits(width: int, track: int, traits: int, n_food: int) -> list[int]:
    return [viv_energy_q(i, width, track, traits) for i in range(n_food)]


def vivarium_coupling_report(qc: QuantumCircuit, width: int, *, track: int = 6,
                             traits: int = VIV_TRAITS,
                             food_sites: tuple[int, ...] = VIV_FOOD_SITES) -> dict[str, Any]:
    """STATIC analyzer of the ASYMMETRIC Weismann barrier (walks qc.data; no statevector):
      * expression        : True iff a gate reads a GENE qubit to set a soma qubit (germ->soma).
      * back_action       : True iff a coherent gate couples a WITNESS LOCUS to a soma qubit
                            (soma->germ; forbidden in vivarium/barren, True in germ_coupled).
      * witness_isolated  : True iff no gate pairs a witness locus with any non-witness qubit.
      * gene_first        : germ (witness) gates precede the life cycle.
      * selection_diagonal: the starve/bud/comparator gates touch no witness locus.
      * has_classical_branch : measure/reset/condition present (must be False -- AC-PJ2.4).
      * gate_counts       : per-operator tally."""
    n_food = len(viv_food_sites(track, food_sites))
    witness = set(viv_witness_qubits(width, track, traits))
    genes = set(viv_gene_qubits(width, track, traits))
    baths = {viv_bath_q(j, width, track, traits, n_food) for j in range(track)}
    soma = set(viv_body_site_qubits(width, track, traits)) | set(viv_food_qubits(width, track, traits)) \
        | set(viv_energy_qubits(width, track, traits, n_food)) | baths

    expression = back_action = has_branch = False
    witness_isolated = True
    gate_counts: dict[str, int] = {}
    for inst in qc.data:
        name = inst.operation.name
        gate_counts[name] = gate_counts.get(name, 0) + 1
        cond = getattr(inst.operation, "condition", None) or getattr(inst, "condition", None)
        if cond is not None or name in ("measure", "reset"):
            has_branch = True
        if name in ("barrier", "delay"):
            continue
        qs = [_qubit_index(qc, b) for b in inst.qubits]
        tw = any(q in witness for q in qs)
        tg = any(q in genes for q in qs)
        ts = any(q in soma for q in qs)
        if tg and ts:
            expression = True
        if tw and ts:
            back_action = True
        if tw and any(q not in witness for q in qs):
            witness_isolated = False

    return {
        "expression": expression,
        "back_action": back_action,
        "witness_isolated": witness_isolated,
        "gene_first": _viv_gene_first(qc, witness, soma | genes),
        "selection_diagonal": not back_action,
        "has_classical_branch": has_branch,
        "witness_set": sorted(witness),
        "gate_counts": gate_counts,
    }


def _viv_gene_first(qc: QuantumCircuit, witness: set[int], rest: set[int]) -> bool:
    """True iff every witness-only gate precedes the first gate touching the soma/genes."""
    last_w = -1
    first_rest = None
    for pos, inst in enumerate(qc.data):
        if inst.operation.name in ("barrier", "delay"):
            continue
        qs = [_qubit_index(qc, b) for b in inst.qubits]
        if any(q in witness for q in qs) and not any(q in rest for q in qs):
            last_w = pos
        if any(q in rest for q in qs) and first_rest is None:
            first_rest = pos
    return (first_rest is None) or (last_w < first_rest)


# ---------------------------------------------------------------------------
# Vivarium --selftest -- STATIC circuit-structure checks (CD-7, no sim).
# ---------------------------------------------------------------------------
def _viv_selftest_case(width: int, track: int, *, steps: int = 3, traits: int = VIV_TRAITS,
                       seed: int = 100) -> list[tuple[str, bool, str]]:
    thetas = q4._sim_thetas(width, seed, mut_scale=0.0)           # faithful clean GHZ
    kw = dict(track=track, traits=traits)
    results: list[tuple[str, bool, str]] = []

    def _build(interaction: str, **extra: Any) -> QuantumCircuit:
        return build_vivarium(width, steps, thetas, interaction=interaction, **kw, **extra)

    rep_v = vivarium_coupling_report(_build("vivarium"), width, **kw)
    rep_b = vivarium_coupling_report(_build("barren"), width, **kw)
    rep_g = vivarium_coupling_report(_build("germ_coupled"), width, **kw)

    # (i) asymmetric barrier: expression True + back_action False for barren/vivarium; germ_coupled breaks it.
    ok_i = (rep_v["expression"] and rep_b["expression"]
            and not rep_v["back_action"] and not rep_b["back_action"]
            and rep_g["back_action"])
    results.append(("asymmetric barrier (expression yes; back-action no; germ_coupled breaks it)",
                    ok_i, f"viv(expr={rep_v['expression']},back={rep_v['back_action']}) "
                    f"germ_coupled_back={rep_g['back_action']}"))

    # (ii) witness isolated in barren/vivarium.
    ok_ii = rep_v["witness_isolated"] and rep_b["witness_isolated"] and not rep_g["witness_isolated"]
    results.append(("witness loci isolated (vivarium/barren) but not germ_coupled",
                    ok_ii, f"viv={rep_v['witness_isolated']} germ_coupled={rep_g['witness_isolated']}"))

    # (iii) germ-first ordering.
    results.append(("ordering: germ line built before the life cycle (rung 0)",
                    rep_v["gene_first"], f"gene_first={rep_v['gene_first']}"))

    # (iv) witness readout isolation: H on witness loci only.
    meas = viv_to_witness_basis(_build("vivarium"), width, **kw)
    witness = set(viv_witness_qubits(width, track, traits))
    h_w = h_o = 0
    for inst in meas.data:
        if inst.operation.name != "h":
            continue
        for b in inst.qubits:
            (h_w := h_w + 1) if _qubit_index(meas, b) in witness else (h_o := h_o + 1)  # type: ignore
    ok_iv = (h_w == width) and (h_o == 0)
    results.append(("witness readout: H on witness loci only", ok_iv, f"H(witness)={h_w} H(other)={h_o}"))

    # (v) no classical branch on the body/selection path (emergent, not if(ate)).
    ok_v = not rep_v["has_classical_branch"] and not rep_b["has_classical_branch"]
    results.append(("no classical branch (fully unitary life cycle)",
                    ok_v, f"viv_branch={rep_v['has_classical_branch']}"))

    # (vi) selection laws diagonal / touch no witness locus.
    results.append(("selection laws touch no witness locus (diagonal)",
                    rep_v["selection_diagonal"], f"selection_diagonal={rep_v['selection_diagonal']}"))

    # (vii) barren == vivarium minus the food seed (SAME law, different seed = emergence).
    n_food = len(viv_food_sites(track))
    x_v = rep_v["gate_counts"].get("x", 0)
    x_b = rep_b["gate_counts"].get("x", 0)
    other_v = {k: v for k, v in rep_v["gate_counts"].items() if k != "x"}
    other_b = {k: v for k, v in rep_b["gate_counts"].items() if k != "x"}
    ok_vii = (x_v - x_b == n_food) and (other_v == other_b)
    results.append(("barren == vivarium minus food seed (identical law, different seed)",
                    ok_vii, f"extra_x_seed={x_v - x_b} expected={n_food} "
                    f"non_seed_gates_equal={other_v == other_b}"))
    return results


def run_vivarium_selftest(cases: tuple[tuple[int, int], ...] = ((2, 5), (4, 6), (12, 6)),
                          steps: int = 3) -> int:
    """Run the seven vivarium static checks at representative (W, track). Return 0/1."""
    print("=== PJ2 solo-vivarium --selftest (STATIC circuit-structure checks; no sim) ===")
    all_ok = True
    for w, track in cases:
        print(f"\n-- vivarium W={w}, track={track}, steps={steps} --")
        for name, ok, detail in _viv_selftest_case(w, track, steps=steps):
            all_ok = all_ok and ok
            print(f"  [{'OK ' if ok else 'FAIL'}] {name}  ({detail})")
    print("\nSELFTEST PASS" if all_ok else "\nSELFTEST FAIL")
    return 0 if all_ok else 1


def print_vivarium_report(width: int, steps: int, thetas: list[float], *, track: int,
                          traits: int, interaction: str, hard_select: bool, gate_repl: bool) -> None:
    """Build the vivarium circuit, print it + a legend + the STATIC correctness report."""
    qc = build_vivarium(width, steps, thetas, track=track, traits=traits, interaction=interaction,
                        hard_select=hard_select, gate_repl=gate_repl, annotate=True)
    rep = vivarium_coupling_report(qc, width, track=track, traits=traits)
    sites = viv_food_sites(track)

    print(f"\n--- PJ2 SOLO-VIVARIUM CIRCUIT (W={width}, track={track}, steps={steps}, "
          f"interaction={interaction}, hard_select={hard_select}, gate_repl={gate_repl}) ---")
    w0 = viv_witness_q(0, width, track, traits)
    g0 = viv_gene_q(0, width, track, traits)
    b0 = viv_body_q(0, width, track, traits)
    f0 = viv_food_q(0, width, track, traits)
    e0 = viv_energy_q(0, width, track, traits)
    print(f"  layout: witness g_k = {w0}..{w0 + width - 1}  |  genes = {g0}..{g0 + traits - 1}  |  "
          f"body = {b0}..{b0 + track - 1}  |  food = {f0}..{f0 + track - 1}  |  "
          f"energy = {e0}..{e0 + len(sites) - 1}")
    print(f"  feeding stations (seeded unless barren): {list(sites)}")
    print("  gate -> meaning:")
    print("    Ry(pi/2)/CX/Ry(theta) on witness = FOUNDER / SELF-REPLICATION / MUTATION (clean GHZ)")
    print("    X on gene ; CX(gene_role -> body) = set genome ; EXPRESS the body (germ->soma)")
    print("    X on food site                   = habitat resource (seeded)")
    print("    RXX+RYY on NN body sites         = H_forage (quantum-walk hop; role-scaled)")
    print("    CCX(body,food -> energy)+CX      = H_eat (emergent consumption on co-location)")
    print("    CCX(energy,body -> body+1)       = H_bud (fed body reproduces)")
    print("    CRY+CX(body,bath) ; CX(energy->body) = death (age all) + REVIVE fed (fittest survive)")
    if interaction == "germ_coupled" or gate_repl:
        print("    RXX+RYY body<->witness_q(0)      = A/B back-action (breaks the barrier)")
    print("    H on witness then measure         = witness readout; soma stays diagonal (Z)")

    print("\n" + str(qc.draw(output="text", fold=-1)))

    print("\n--- STATIC VIVARIUM CORRECTNESS REPORT (asymmetric Weismann barrier) ---")
    print(f"  germ->soma expression present:            {'YES' if rep['expression'] else 'NO'}")
    print(f"  soma->germ back-action (must be NO here):  {'YES' if rep['back_action'] else 'NO'}")
    print(f"  witness loci isolated:                    {'YES' if rep['witness_isolated'] else 'NO'}")
    print(f"  germ passed before the life cycle:        {'YES' if rep['gene_first'] else 'NO'}")
    print(f"  selection laws touch no witness locus:    {'YES' if rep['selection_diagonal'] else 'NO'}")
    print(f"  classical branch on body path (must NO):  {'YES' if rep['has_classical_branch'] else 'NO'}")
    print(f"  witness qubit set (germ line):            {rep['witness_set']}")
    print(f"  gate counts:                              {rep['gate_counts']}")


# ===========================================================================
# PJ2.2: THE 2D-LATTICE VIVARIUM -- a walking occupancy field + germ witness.
# ---------------------------------------------------------------------------
# Built ALONGSIDE PJ0/PJ1/PJ2 (build_germsoma / build_arena / build_vivarium untouched,
# byte-stable). A DIFFERENT substrate from the 1D vivarium: the organism is a pure
# UNARY OCCUPANCY FIELD on a grid x grid square lattice (one qubit per cell, index
# i = r*grid + c) that WALKS -- each generation is one Trotter layer of an excitation-
# conserving rxx+ryy quantum walk between von-Neumann neighbours (mass conserved, nothing
# scripted). Eating/energy/budding are deliberately CUT as overclaiming (mockup README §1:
# "the honest scope is movement + witness only"). The single quantum claim is the germ-line
# genealogical witness <X^W>, reusing PJ0's GHZ machinery. Three modes (solo / replicate /
# duo) x two arms (isolated germ line / coupled = the soma->germ wound). Certified frames are
# a DEPTH SCAN: each generation is its own measured circuit (README §5), not a sim-movie.
# ===========================================================================

# Fixed lattice laws (build-time defaults for --dump-circuit / --selftest structural checks).
LAT_HOP = 0.6                        # isotropic quantum-walk hop angle (OQ-4; uniform theta)
LAT_MODES = ("solo", "replicate", "duo")
LAT_ARMS = ("isolated", "coupled")
LAT_REP_GEN = 2                      # generation the germ line CNOT-clones (README §1/§7)


# ---------------------------------------------------------------------------
# Lattice layout: per organism [germ witness (W) | unary body field (grid*grid)],
# organisms in contiguous adjacent blocks (clean per-organism GHZ genealogy).
# ---------------------------------------------------------------------------
def lat_n_organisms(mode: str) -> int:
    """Fields present: 1 (solo) / 2 (replicate: parent+daughter) / 2 (duo)."""
    if mode == "solo":
        return 1
    if mode in ("replicate", "duo"):
        return 2
    raise ValueError(f"unknown lattice mode {mode!r}")


def lat_segment_len(width: int, grid: int, mode: str) -> int:
    """Qubit span: n_organisms * (germ width W + grid*grid body cells).
    3x3 solo = 12, 3x3 replicate/duo = 24, 4x4 solo = 19 (all fit sim _SV_MAX_QUBITS/Heron)."""
    return lat_n_organisms(mode) * (width + grid * grid)


def lat_base(org: int, width: int, grid: int) -> int:
    """First physical qubit of organism `org` (adjacent segments)."""
    return org * (width + grid * grid)


def lat_witness_q(org: int, k: int, width: int, grid: int) -> int:
    """Germ-line witness locus k of organism `org` (front of its block; the GHZ genealogy)."""
    return lat_base(org, width, grid) + k


def lat_body_q(org: int, i: int, width: int, grid: int) -> int:
    """Body cell i = r*grid + c of organism `org` -- one excitation = where the body is."""
    return lat_base(org, width, grid) + width + i


def lat_neighbors(i: int, grid: int) -> list[int]:
    """Von-Neumann neighbours of cell i = r*grid + c on a grid x grid lattice."""
    r, c = divmod(i, grid)
    nb: list[int] = []
    if r > 0:
        nb.append((r - 1) * grid + c)
    if r < grid - 1:
        nb.append((r + 1) * grid + c)
    if c > 0:
        nb.append(r * grid + (c - 1))
    if c < grid - 1:
        nb.append(r * grid + (c + 1))
    return nb


def lat_edges(grid: int) -> list[list[tuple[int, int]]]:
    """Von-Neumann edges grouped into 4 disjoint colors (H-even / H-odd / V-even / V-odd) so
    each color is a depth-1 layer of non-overlapping 2-qubit gates (keeps the walk shallow)."""
    h_even: list[tuple[int, int]] = []
    h_odd: list[tuple[int, int]] = []
    v_even: list[tuple[int, int]] = []
    v_odd: list[tuple[int, int]] = []
    for r in range(grid):
        for c in range(grid):
            i = r * grid + c
            if c < grid - 1:
                (h_even if c % 2 == 0 else h_odd).append((i, i + 1))
            if r < grid - 1:
                (v_even if r % 2 == 0 else v_odd).append((i, i + grid))
    return [h_even, h_odd, v_even, v_odd]


# ---------------------------------------------------------------------------
# The 2D-lattice model -- germ line(s) first, seed, `gens` von-Neumann walk layers.
# ---------------------------------------------------------------------------
def _lattice_germ(qc: QuantumCircuit, org: int, width: int, grid: int, thetas: list[float],
                  founder_equator: bool) -> None:
    """One organism's germ line (rung 0): founder ry(pi/2) + NN cx clone chain + ry(theta)
    mutation -- the clean GHZ genealogy carrying <X^W> (reuse of the PJ0 germ pattern)."""
    for k in range(width):
        g = lat_witness_q(org, k, width, grid)
        if k == 0:
            if founder_equator:
                qc.ry(math.pi / 2, g)                              # FOUNDER
        else:
            qc.cx(lat_witness_q(org, k - 1, width, grid), g)       # SELF-REPLICATION (NN clone)
        qc.ry(thetas[k], g)                                        # MUTATION


def _lattice_walk_layer(qc: QuantumCircuit, grid: int, org: int, width: int, theta: float) -> None:
    """One Trotter walk layer: excitation-conserving rxx(theta)+ryy(theta) on every von-Neumann
    neighbour pair of organism `org`'s body block, in edge-colored order. Applied UNCONDITIONALLY
    (no if/c_if on position); germ untouched -- the bodies move, mass conserved."""
    for color in lat_edges(grid):
        for a_cell, b_cell in color:
            a = lat_body_q(org, a_cell, width, grid)
            b = lat_body_q(org, b_cell, width, grid)
            qc.rxx(theta, a, b)
            qc.ryy(theta, a, b)


def _lattice_clone(qc: QuantumCircuit, width: int, grid: int, start: int, hop: float) -> None:
    """Replicate: CNOT-clone the parent germ line into the daughter germ block (germ->germ only,
    the shared GHZ) and seed a daughter body one cell over (down-neighbour of the seed)."""
    for k in range(width):
        qc.cx(lat_witness_q(0, k, width, grid), lat_witness_q(1, k, width, grid))
    n_cells = grid * grid
    dstart = start + grid if start + grid < n_cells else (start + 1) % n_cells
    qc.x(lat_body_q(1, dstart, width, grid))


def _lattice_interaction(qc: QuantumCircuit, width: int, grid: int, phi: float) -> None:
    """Duo: co-located rxx+ryy between organism A and B body cells (emergent from co-location,
    no if(contact)); it only acts where both bodies have amplitude -- builds the joint witness."""
    for i in range(grid * grid):
        a = lat_body_q(0, i, width, grid)
        b = lat_body_q(1, i, width, grid)
        qc.rxx(phi, a, b)
        qc.ryy(phi, a, b)


def build_lattice_vivarium(width: int, grid: int, gens: int, thetas: list[float], *,
                           mode: str = "solo", arm: str = "isolated", start: int = 0,
                           hop: float = LAT_HOP, founder_equator: bool = True,
                           annotate: bool = False) -> QuantumCircuit:
    """One walking occupancy field after `gens` walk layers, in ONE circuit (built once per depth
    for the driver's depth scan).

    mode : 'solo'      -- one field walks; mass conserved, nothing eaten or born.
           'replicate' -- at gen LAT_REP_GEN the germ line is CNOT-cloned into a daughter (one
                          shared GHZ) + a daughter body seeded one cell over.
           'duo'       -- two fields at opposite corners drift together; co-located rxx+ryy body
                          interaction builds a joint two-body witness.
    arm  : 'isolated'  -- never couples a body cell to a germ qubit (Weismann barrier intact).
           'coupled'   -- one coherent rxx+ryy body<->witness-locus gate (the soma->germ wound;
                          the A/B kill-switch -> the witness collapses).
    Phases: (1) germ line(s) first; (2) seed the body/bodies; (3) `gens` von-Neumann walk layers
    (replicate germ-clone at gen 2; duo co-located interaction per layer); (4) coupled-arm wound.
    """
    if mode not in LAT_MODES:
        raise ValueError(f"unknown lattice mode {mode!r}")
    if arm not in LAT_ARMS:
        raise ValueError(f"unknown lattice arm {arm!r}")
    n_cells = grid * grid
    n_data = lat_segment_len(width, grid, mode)
    qc = QuantumCircuit(n_data)

    # --- Phase 1: germ line(s) first. solo/replicate build ONLY the parent (the daughter germ is
    #     cloned from it at gen 2); duo builds two INDEPENDENT founders (joined via interaction). ---
    _lattice_germ(qc, 0, width, grid, thetas, founder_equator)
    if mode == "duo":
        _lattice_germ(qc, 1, width, grid, thetas, founder_equator)
    _bar(qc, annotate, "germline")

    # --- Phase 2: seed the body (one excitation = the start cell). duo seeds opposite corners. ---
    start = start % n_cells
    if mode == "duo":
        qc.x(lat_body_q(0, 0, width, grid))                       # corner 0
        qc.x(lat_body_q(1, n_cells - 1, width, grid))             # opposite corner
    else:
        qc.x(lat_body_q(0, start, width, grid))
    _bar(qc, annotate, "seed")

    # --- Phase 3: `gens` walk layers (barrier per layer). ---
    daughter = False
    for gen in range(int(gens)):
        if mode == "replicate" and gen == LAT_REP_GEN:
            _lattice_clone(qc, width, grid, start, hop)
            daughter = True
            _bar(qc, annotate, "replicate")
        _lattice_walk_layer(qc, grid, 0, width, hop)
        if daughter:
            _lattice_walk_layer(qc, grid, 1, width, hop)
        if mode == "duo":
            _lattice_walk_layer(qc, grid, 1, width, hop)
            _lattice_interaction(qc, width, grid, hop)
        _bar(qc, annotate, f"walk{gen}")
    if mode == "replicate" and not daughter and int(gens) >= LAT_REP_GEN:
        _lattice_clone(qc, width, grid, start, hop)                # spawn at exactly gen == 2
        daughter = True
        _bar(qc, annotate, "replicate")

    # --- Phase 4: coupled arm -- the soma->germ back-action (breaks the Weismann barrier). ---
    if arm == "coupled":
        centre = (grid // 2) * grid + (grid // 2)
        b = lat_body_q(0, centre, width, grid)
        g = lat_witness_q(0, 0, width, grid)
        qc.rxx(math.pi / 2, b, g)
        qc.ryy(math.pi / 2, b, g)
        _bar(qc, annotate, "arm")

    return qc


def lattice_to_witness_basis(qc: QuantumCircuit, width: int, grid: int, mode: str) -> QuantumCircuit:
    """Rotate the germ loci into the X basis (H then Z-read). Body cells stay in Z (diagonal --
    excluded from the witness, CD-3). Returns a NEW circuit."""
    out = qc.copy()
    for q in lattice_witness_qubits(width, grid, mode):
        out.h(q)
    return out


# ---------------------------------------------------------------------------
# Lattice observables + static analysis (build-time only -- NO execution).
# ---------------------------------------------------------------------------
def lattice_witness_qubits(width: int, grid: int, mode: str) -> list[int]:
    """The witness loci -- every organism's germ line (the joint <X^W> set; CD-3)."""
    return [lat_witness_q(o, k, width, grid)
            for o in range(lat_n_organisms(mode)) for k in range(width)]


def lattice_body_qubits(org: int, width: int, grid: int) -> list[int]:
    """The body cells of organism `org` (the unary occupancy field)."""
    return [lat_body_q(org, i, width, grid) for i in range(grid * grid)]


def lattice_coupling_report(qc: QuantumCircuit, width: int, grid: int, *, mode: str,
                            arm: str) -> dict[str, Any]:
    """STATIC analyzer of the Weismann barrier under 2D movement (walks qc.data; no statevector):
      * back_action     : True iff a gate couples a WITNESS locus to a BODY cell (soma->germ;
                          forbidden in isolated, present in coupled).
      * witness_isolated: True iff no gate pairs a witness locus with a non-witness qubit (the
                          germ->germ replicate clone keeps this True -- both ends are witness).
      * mass_conserved  : True iff every body-touching multi-qubit gate is rxx/ryy (excitation-
                          conserving; the seed x is the only 1-qubit body gate).
      * germ_first      : germ line built before the body starts (founder precedes the seed).
      * has_classical_branch : measure/reset/condition present (must be False -- AC-PJ2.2.3).
      * gate_counts     : per-operator tally."""
    witness = set(lattice_witness_qubits(width, grid, mode))
    body: set[int] = set()
    for o in range(lat_n_organisms(mode)):
        body |= set(lattice_body_qubits(o, width, grid))

    back_action = has_branch = False
    witness_isolated = mass_conserved = True
    first_germ_pos: int | None = None
    first_body_pos: int | None = None
    gate_counts: dict[str, int] = {}
    for pos, inst in enumerate(qc.data):
        name = inst.operation.name
        gate_counts[name] = gate_counts.get(name, 0) + 1
        cond = getattr(inst.operation, "condition", None) or getattr(inst, "condition", None)
        if cond is not None or name in ("measure", "reset"):
            has_branch = True
        if name in ("barrier", "delay"):
            continue
        qs = [_qubit_index(qc, b) for b in inst.qubits]
        tw = any(q in witness for q in qs)
        tb = any(q in body for q in qs)
        if tw and first_germ_pos is None:
            first_germ_pos = pos
        if tb and first_body_pos is None:
            first_body_pos = pos
        if tw and tb:
            back_action = True
        if tw and any(q not in witness for q in qs):
            witness_isolated = False
        if tb and name not in ("rxx", "ryy", "x"):
            mass_conserved = False

    germ_first = first_germ_pos is not None and (first_body_pos is None
                                                 or first_germ_pos < first_body_pos)
    return {
        "back_action": back_action,
        "witness_isolated": witness_isolated,
        "mass_conserved": mass_conserved,
        "germ_first": germ_first,
        "has_classical_branch": has_branch,
        "witness_set": sorted(witness),
        "gate_counts": gate_counts,
    }


# ---------------------------------------------------------------------------
# Lattice --selftest -- STATIC circuit-structure checks (CD-7, no sim).
# ---------------------------------------------------------------------------
def _lattice_selftest_case(grid: int, mode: str, *, width: int = 3, gens: int = 4,
                           seed: int = 100) -> list[tuple[str, bool, str]]:
    thetas = q4._sim_thetas(width, seed, mut_scale=0.0)           # faithful clean GHZ
    results: list[tuple[str, bool, str]] = []

    def _build(arm: str) -> QuantumCircuit:
        return build_lattice_vivarium(width, grid, gens, thetas, mode=mode, arm=arm)

    rep_i = lattice_coupling_report(_build("isolated"), width, grid, mode=mode, arm="isolated")
    rep_c = lattice_coupling_report(_build("coupled"), width, grid, mode=mode, arm="coupled")

    # (i) A/B kill-switch: isolated has no back-action; coupled breaks the barrier.
    ok_i = (not rep_i["back_action"]) and rep_c["back_action"]
    results.append(("A/B kill-switch (isolated no back-action; coupled breaks it)",
                    ok_i, f"isolated_back={rep_i['back_action']} coupled_back={rep_c['back_action']}"))

    # (ii) witness isolated in the isolated arm (germ->germ clone stays witness-internal).
    results.append(("witness loci isolated (isolated arm) but not coupled",
                    rep_i["witness_isolated"] and not rep_c["witness_isolated"],
                    f"isolated={rep_i['witness_isolated']} coupled={rep_c['witness_isolated']}"))

    # (iii) mass conserved: the walk is rxx+ryy neighbour pairs only.
    results.append(("mass conserved (walk = rxx+ryy neighbour pairs)",
                    rep_i["mass_conserved"], f"mass_conserved={rep_i['mass_conserved']}"))

    # (iv) germ-first ordering (germ line before the body moves).
    results.append(("ordering: germ line built before the body (rung 0)",
                    rep_i["germ_first"], f"germ_first={rep_i['germ_first']}"))

    # (v) witness readout isolation: H on the germ loci only.
    meas = lattice_to_witness_basis(_build("isolated"), width, grid, mode)
    witness = set(lattice_witness_qubits(width, grid, mode))
    h_w = h_o = 0
    for inst in meas.data:
        if inst.operation.name != "h":
            continue
        for b in inst.qubits:
            (h_w := h_w + 1) if _qubit_index(meas, b) in witness else (h_o := h_o + 1)  # type: ignore
    ok_v = (h_w == len(witness)) and (h_o == 0)
    results.append(("witness readout: H on germ loci only", ok_v, f"H(witness)={h_w} H(other)={h_o}"))

    # (vi) no classical branch (fully unitary walk -- no if/measure/reset).
    results.append(("no classical branch (fully unitary walk)",
                    not rep_i["has_classical_branch"], f"branch={rep_i['has_classical_branch']}"))

    # (vii) qubit count matches lat_segment_len.
    nq = _build("isolated").num_qubits
    expect = lat_segment_len(width, grid, mode)
    results.append(("qubit count == lat_segment_len(width, grid, mode)",
                    nq == expect, f"nq={nq} expected={expect}"))
    return results


def run_lattice_selftest(cases: tuple[tuple[int, str], ...] = ((3, "solo"), (3, "replicate"),
                                                               (3, "duo"), (4, "solo")),
                         width: int = 3, gens: int = 4) -> int:
    """Run the seven lattice static checks at representative (grid, mode). Return 0/1."""
    print("=== PJ2.2 2D-lattice vivarium --selftest (STATIC circuit-structure checks; no sim) ===")
    all_ok = True
    for grid, mode in cases:
        nq = lat_segment_len(width, grid, mode)
        print(f"\n-- lattice grid={grid}x{grid}, mode={mode}, W={width}, gens={gens} ({nq} qubits) --")
        for name, ok, detail in _lattice_selftest_case(grid, mode, width=width, gens=gens):
            all_ok = all_ok and ok
            print(f"  [{'OK ' if ok else 'FAIL'}] {name}  ({detail})")
    print("\nSELFTEST PASS" if all_ok else "\nSELFTEST FAIL")
    return 0 if all_ok else 1


def print_lattice_report(width: int, grid: int, gens: int, thetas: list[float], *, mode: str,
                         arm: str) -> None:
    """Build the lattice circuit, print it + a legend + the STATIC correctness report."""
    qc = build_lattice_vivarium(width, grid, gens, thetas, mode=mode, arm=arm, annotate=True)
    rep = lattice_coupling_report(qc, width, grid, mode=mode, arm=arm)

    print(f"\n--- PJ2.2 2D-LATTICE VIVARIUM CIRCUIT (W={width}, grid={grid}x{grid}, gens={gens}, "
          f"mode={mode}, arm={arm}) ---")
    n_org = lat_n_organisms(mode)
    for o in range(n_org):
        w0 = lat_witness_q(o, 0, width, grid)
        b0 = lat_body_q(o, 0, width, grid)
        print(f"  organism {o}: germ g_k = {w0}..{w0 + width - 1}  |  "
              f"body cells = {b0}..{b0 + grid * grid - 1} (i = r*{grid} + c)")
    print("  gate -> meaning:")
    print("    Ry(pi/2)/CX/Ry(theta) on germ = FOUNDER / SELF-REPLICATION / MUTATION (clean GHZ)")
    print("    X on a body cell               = seed the occupancy field at the start cell")
    print("    RXX+RYY on von-Neumann pairs   = the walk (excitation-conserving; mass conserved)")
    if mode == "replicate":
        print(f"    CX germ(0,k)->germ(1,k) @ gen {LAT_REP_GEN} = the daughter germ clone (germ->germ)")
    if mode == "duo":
        print("    RXX+RYY co-located A/B body    = the emergent two-body interaction")
    if arm == "coupled":
        print("    RXX+RYY body<->germ(0,0)       = the A/B back-action (breaks the barrier)")
    print("    H on germ then measure          = witness readout; body stays diagonal (Z)")

    print("\n" + str(qc.draw(output="text", fold=-1)))

    print("\n--- STATIC LATTICE CORRECTNESS REPORT (Weismann barrier under 2D movement) ---")
    print(f"  soma->germ back-action (NO in isolated):  {'YES' if rep['back_action'] else 'NO'}")
    print(f"  witness loci isolated:                    {'YES' if rep['witness_isolated'] else 'NO'}")
    print(f"  mass conserved (rxx+ryy walk):            {'YES' if rep['mass_conserved'] else 'NO'}")
    print(f"  germ line before the body (rung 0):       {'YES' if rep['germ_first'] else 'NO'}")
    print(f"  classical branch (must be NO):            {'YES' if rep['has_classical_branch'] else 'NO'}")
    print(f"  witness qubit set (germ lines):           {rep['witness_set']}")
    print(f"  gate counts:                              {rep['gate_counts']}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ0 germ/soma model + PJ1 arena + PJ2 vivarium (static eval; no sim/hardware).")
    ap.add_argument("--width", type=int, default=12, help="population width W (any W; 12 anchor)")
    ap.add_argument("--steps", type=int, default=6, help="life-cycle steps")
    ap.add_argument("--soma-death", dest="soma_death",
                    choices=["natural", "local_damping", "none"], default="natural",
                    help="natural (gate) | local_damping (reference) | none (control)")
    ap.add_argument("--phenotype", choices=["separable", "entangled"], default="separable",
                    help="separable (faithful) | entangled (A/B: gratuitous cx(g,p))")
    ap.add_argument("--selftest", action="store_true",
                    help="run the static circuit-structure checks and exit")
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print the annotated circuit + static correctness report")
    # --- PJ1 arena flags (default: PJ0 static CLI, unchanged) ---
    ap.add_argument("--arena", action="store_true",
                    help="PJ1: switch to the two-organism arena build")
    ap.add_argument("--organisms", type=int, default=2, help="arena organisms (PJ1: 2)")
    ap.add_argument("--track", type=int, default=6, help="arena unary body-track sites/organism")
    ap.add_argument("--traits", type=int, default=1, help="arena trait qubits/organism (idle hook)")
    ap.add_argument("--interaction", choices=["none", "soma_soma", "germ_routed"],
                    default="soma_soma", help="arena collision arm")
    ap.add_argument("--frame", type=int, default=4, help="arena time-step to build (the clock)")
    # --- PJ2.2 lattice flags (default: PJ0 static CLI, unchanged) ---
    ap.add_argument("--lattice", action="store_true",
                    help="PJ2.2: switch to the 2D-lattice vivarium build")
    ap.add_argument("--grid", type=int, default=3, help="lattice side (3 or 4)")
    ap.add_argument("--mode", choices=list(LAT_MODES), default="solo", help="lattice scenario")
    ap.add_argument("--arm", choices=list(LAT_ARMS), default="isolated", help="lattice arm")
    ap.add_argument("--gens", type=int, default=5, help="lattice walk generations (depth)")
    # --- PJ2 vivarium flags (default: PJ0 static CLI, unchanged) ---
    ap.add_argument("--vivarium", action="store_true",
                    help="PJ2: switch to the solo-vivarium build")
    ap.add_argument("--viv-interaction", dest="viv_interaction",
                    choices=["vivarium", "barren", "germ_coupled"], default="vivarium",
                    help="vivarium arm")
    ap.add_argument("--hard-select", dest="hard_select", action="store_true",
                    help="append the optional static fitness comparator (contrast)")
    ap.add_argument("--gate-repl", dest="gate_repl", action="store_true",
                    help="route budding through the witness clone (measured-cost variant)")
    args = ap.parse_args()

    if args.lattice:
        if args.selftest:
            raise SystemExit(run_lattice_selftest())
        thetas = q4._sim_thetas(args.width, 0, mut_scale=0.0)   # faithful clean GHZ (CD-6)
        print_lattice_report(args.width, args.grid, args.gens, thetas,
                             mode=args.mode, arm=args.arm)
        return

    if args.vivarium:
        if args.selftest:
            raise SystemExit(run_vivarium_selftest(steps=args.steps))
        thetas = q4._sim_thetas(args.width, 0, mut_scale=0.0)   # faithful clean GHZ (Q5)
        viv_traits = args.traits if args.traits >= VIV_TRAITS else VIV_TRAITS  # arena default is 1
        print_vivarium_report(args.width, args.steps, thetas, track=args.track,
                              traits=viv_traits, interaction=args.viv_interaction,
                              hard_select=args.hard_select, gate_repl=args.gate_repl)
        return

    if args.arena:
        if args.selftest:
            raise SystemExit(run_arena_selftest())
        thetas = q4._sim_thetas(args.width, 0, mut_scale=0.0)   # faithful clean GHZ (Q5)
        print_arena_report(args.width, args.steps, thetas, organisms=args.organisms,
                           track=args.track, traits=args.traits,
                           interaction=args.interaction, frame=args.frame)
        return

    if args.selftest:
        raise SystemExit(run_selftest(steps=args.steps))


    thetas = q4._sim_thetas(args.width, 0, mut_scale=0.0)   # faithful (Q5)
    print_correctness_report(args.width, args.steps, thetas,
                             phenotype=args.phenotype, soma_death=args.soma_death)


if __name__ == "__main__":
    main()
