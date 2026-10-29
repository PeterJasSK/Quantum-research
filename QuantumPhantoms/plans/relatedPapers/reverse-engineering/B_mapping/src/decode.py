"""Shot bitstring -> node states -> TumorDraw fields, with the certificate seed chain."""
import hashlib

from B_mapping.src.compiler import decode_bits
from shared.seedhash import derive_seed, rng


def shot_combos(compiled, memory: list):
    """Per-shot combos (None = invalid code). qiskit memory is MSB-first, clbit i = logical qubit i."""
    out = []
    for bits in memory:
        b = [int(ch) for ch in reversed(bits.replace(" ", ""))]
        out.append(decode_bits(compiled, b))
    return out


def select_shot(combos: list, cert_seed: str) -> int:
    """Seeded shot index; invalid shots are skipped forward (wrapping) to the next valid one."""
    n = len(combos)
    start = derive_seed(cert_seed, "B.shot_select") % n
    for off in range(n):
        i = (start + off) % n
        if combos[i] is not None:
            return i
    raise ValueError("no valid shot in job")


def size_in_bin(bin_label: str, cert_seed: str) -> float:
    lo, hi = (float(x) for x in bin_label.split("-"))
    return round(lo + (hi - lo) * float(rng(cert_seed, "B.size").random()), 3) or lo


def shape_seed_hex(cert_seed: str, draw_id: str) -> str:
    return hashlib.sha256(bytes.fromhex(cert_seed) + b"B.shape" + draw_id.encode()).hexdigest()


def to_draw(compiled, combo: tuple, shot_index: int, cert_seed: str, site_id: str | None) -> dict:
    """TumorDraw body (no envelope). site_id from the shot for B-2, else given."""
    st = {nm: compiled.states[i][c] for i, (nm, c) in enumerate(zip(compiled.nodes, combo))}
    draw_id = f"B{shot_index:06d}"
    return {
        "draw_id": draw_id,
        "site_id": st.get("site", site_id),
        "size_mm": size_in_bin(st["size_bin"], cert_seed),
        "type": st["tumor_type"],
        "margin": st["margin"],
        "shape_seed_hex": shape_seed_hex(cert_seed, draw_id),
        "shot_index": shot_index,
    }
