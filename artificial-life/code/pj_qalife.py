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


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ0 germ/soma model + PJ1 arena (static evaluation; no sim, no hardware).")
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
    args = ap.parse_args()

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
