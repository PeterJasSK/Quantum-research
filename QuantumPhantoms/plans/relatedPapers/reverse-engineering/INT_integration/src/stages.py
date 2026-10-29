"""The 9 chain stages as data: one Step per letter-CLI call, with argv built from upstream contract paths.

A Step never imports letter code (epic rule). It names a module run as `python -m <module>`, its argv (literal
strings, or Ref("<ctx key>") filled from earlier outputs), the files it leaves in its new run directory, and checks
that turn what it produced into findings or a StageFail. Findings are the point of INT: every gap between what
the plan's chain needs and what the letters do today is written down, never silently adapted.

Finding kinds: gap (CLI arg / behaviour the plan needs is missing), contract (an unapplied CCR shows up in the
data), weak-link (works, but limits reliability), precondition (environment / data / cost), info.
Severities: block (the chain cannot pass this step), warn, info.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from shared import LETTERS, RE_ROOT, SHARED
from shared.seedhash import code_hash, derive_seed

G_RUNS = RE_ROOT / LETTERS["G"] / "runs"
KEYS = G_RUNS / "keys"
LEDGER = G_RUNS / "ledger.jsonl"
BEACON_CACHE = RE_ROOT / LETTERS["C"] / "repro" / "data" / "beacon_pulses.json"
A_CACHE = RE_ROOT / LETTERS["A"] / "runs" / "cache"
E_PARAMS = RE_ROOT / LETTERS["E"] / "src" / "params_lung.json"
RULEBOOK = "B_mapping/data/rulebook_lung.json"
LIBRARY = "F_render/library/lesion_model_library.json"
PARAM_FILES = ("B_mapping/data/class_prior.json", "E_classical_growth/src/params_lung.json", LIBRARY)
NON_RUN_DIRS = {"cache", "keys"}
FETCH_TRIES = 10


class Ref(str):
    """argv placeholder: replaced by ctx[<key>] (usually a contract path) when the step runs."""


class StageFail(Exception):
    def __init__(self, msg: str, code: int = 1):
        super().__init__(msg)
        self.code = code


def finding(kind: str, severity: str, msg: str, step: str = "") -> dict:
    return {"step": step, "kind": kind, "severity": severity, "msg": msg}


@dataclass
class Step:
    name: str                                   # "<letter>.<what>", e.g. "C.certify"
    letter: str                                 # "A".."H", or "INT" for runner-local steps
    module: str | None = None                   # python -m <module>
    args: list = field(default_factory=list)    # str | Ref
    outputs: dict = field(default_factory=dict)  # ctx key -> path in the new run dir ("." = the run dir)
    run_dir: bool = True                        # the CLI creates <letter>/runs/<ts>-<tag>/
    optional: bool = False                      # a gap or failure is recorded, the chain continues
    skip: Callable | None = None                # ctx -> (reason, {key: path}) | None (cache hit)
    pre: Callable | None = None                 # ctx -> [finding]
    post: Callable | None = None                # ctx -> [finding]; may raise StageFail
    func: Callable | None = None                # runner-local step: (ctx, chain_dir) -> {key: path}
    probe: Callable | None = None               # ctx -> [finding]; static preconditions, nothing runs

    @property
    def folder(self) -> Path:
        return RE_ROOT / LETTERS.get(self.letter, "INT_integration")

    def interpreter(self, ctx: dict) -> str:
        return ctx["python_a"] if self.letter == "A" else ctx["python"]

    def subcommand(self) -> list[str]:
        """Leading literal positionals (e.g. `receipt fill`): needed to ask the right subparser for --help."""
        lead = []
        for a in self.args:
            if isinstance(a, Ref) or a.startswith("-"):
                break
            lead.append(a)
        return lead

    def flags(self) -> list[str]:
        return [a for a in self.args if not isinstance(a, Ref) and a.startswith("--")]


# ---------------------------------------------------------------------------------------------- helpers

def rel(p) -> str:
    p = Path(p)
    try:
        return p.resolve().relative_to(RE_ROOT).as_posix()
    except ValueError:
        return str(p)


def load(p) -> dict:
    return json.loads(Path(RE_ROOT / p).read_text())


def resolve_args(step: Step, ctx: dict, strict: bool = True) -> list[str]:
    out = []
    for a in step.args:
        if isinstance(a, Ref):
            v = ctx.get(str(a))
            if v is None:
                if strict:
                    raise StageFail(f"{step.name}: upstream value '{a}' is missing (earlier stage not run or reused)")
                v = f"<{a}>"
            out.append(rel(v) if isinstance(v, (str, Path)) and ("/" in str(v)) else str(v))
        else:
            out.append(a)
    return out


def letter_code_hash(letter: str) -> str:
    """Same tree hash start_run and G's commit use: [letter folder, shared/]."""
    return code_hash([RE_ROOT / LETTERS[letter], SHARED])


def _iso(ts: str) -> str:
    return ts[:19]


_FLAG = re.compile(r"(?<![\w-])--[a-zA-Z][\w-]*")


def cli_help(py: str, step: Step) -> dict:
    """Ask the letter's own argparse which flags exist and which are required (no letter import here)."""
    argv = [py, "-m", step.module, *step.subcommand(), "--help"]
    try:
        r = subprocess.run(argv, cwd=RE_ROOT, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr or r.stdout).strip().splitlines()[-1:] or ["no output"]}
    text = r.stdout
    usage = text.split("\n\n", 1)[0]
    flat = usage
    while True:  # strip optional [..] groups; what is left in the usage line is required
        nxt = re.sub(r"\[[^\[\]]*\]", "", flat)
        if nxt == flat:
            break
        flat = nxt
    return {"ok": True, "flags": sorted(set(_FLAG.findall(text))), "required": sorted(set(_FLAG.findall(flat)))}


def repeat_ok(step: Step, flag: str) -> bool:
    """A flag the plan repeats must be action='append' in the letter source (read as text, not imported)."""
    src = RE_ROOT / (step.module.replace(".", "/") + ".py")
    pat = re.compile(r"add_argument\(\s*['\"]" + re.escape(flag) + r"['\"][^)]*action\s*=\s*['\"](append|extend)")
    return bool(pat.search(src.read_text())) if src.is_file() else False


def cli_findings(step: Step, help_: dict) -> list[dict]:
    sev = "warn" if step.optional else "block"
    if not help_.get("ok"):
        return [finding("gap", sev, f"`python -m {step.module} --help` failed: {help_.get('error')}", step.name)]
    out = []
    used = step.flags()
    for f in sorted(set(used)):
        if f not in help_["flags"]:
            out.append(finding("gap", sev, f"flag `{f}` does not exist in `{step.module}`", step.name))
        elif used.count(f) > 1 and not repeat_ok(step, f):
            out.append(finding("gap", sev, f"`{f}` is passed {used.count(f)}× but is not action='append': argparse "
                                           f"keeps only the last value", step.name))
    for f in help_["required"]:
        if f not in used:
            out.append(finding("gap", sev, f"`{step.module}` requires `{f}`, which the plan's chain does not supply",
                               step.name))
    return out


# ---------------------------------------------------------------------------------------------- stage checks

def _skip_keys(ctx):
    return ("demo signing key already exists", {}) if (KEYS / "signing_key.pem").is_file() else None


def _probe_keys(ctx):
    return [finding("weak-link", "info", "G signs with a per-machine demo Ed25519 key pinned in trusted_keys.json "
                                         "(no PKI / HSM)", "G.keys")]


def _probe_commit(ctx):
    """The commit freezes .py code (code_hash) + the rulebook file; parameter JSON read by the code is outside it."""
    params = [p for p in PARAM_FILES if (RE_ROOT / p).is_file()]
    if not params:
        return []
    return [finding("weak-link", "warn", f"commit code_hash covers *.py only: {len(params)} parameter JSON files "
                                         f"({', '.join(params)}) can change after the commit without breaking G's "
                                         f"code-hash check", "G.commit")]


def _post_commit(ctx):
    rc, man = load(ctx["G.commit_receipt"]), load(ctx["G.commit_manifest"])
    ctx["commit_utc"] = rc["commit"]["committed_utc"]
    ctx["code_hashes"] = man.get("code_hashes", {})
    out = []
    missing = [L for L in LETTERS if L not in ctx["code_hashes"]]
    if missing:
        out.append(finding("weak-link", "warn", f"commit freezes code of {''.join(sorted(ctx['code_hashes']))} only; "
                                                f"{', '.join(missing)} can change after the commit unnoticed", "G.commit"))
    if LEDGER.is_file():
        last = json.loads(LEDGER.read_text().strip().splitlines()[-1])
        if last.get("kind") != "commit":
            out.append(finding("contract", "warn", f"ledger entry for the commit has kind '{last.get('kind')}', "
                                                   f"not 'commit' (CCR-G1 unapplied)", "G.commit"))
    return out


def _probe_fetch(ctx):
    out = [finding("weak-link", "warn", f"fetch_pulses overwrites the git-tracked cache {rel(BEACON_CACHE)} in place "
                                        f"and creates no run dir: a chain run dirties the repo", "C.fetch")]
    if BEACON_CACHE.is_file():
        c = json.loads(BEACON_CACHE.read_text())
        out.append(finding("precondition", "info", f"cached pulses fetched {c.get('fetched_utc')}; without network "
                                                   f"the chain falls back to them (beacon_fresh: false)", "C.fetch"))
    return out


def _fetch_after_commit(ctx, chain_dir):
    """Run C's fetch_pulses until the newest cached NIST pulse postdates the commit.

    Pulses are 60 s apart and /pulse/last lags the wall clock by ~2 min, so one fetch right after the commit always
    returns an older pulse. Re-fetch every 30 s for up to FETCH_TRIES; on a network error keep the cache
    (beacon_fetched: false). This retries the public-input fetch, never a certificate.
    """
    import time

    tries = []
    for i in range(FETCH_TRIES):
        r = subprocess.run([ctx["python"], "-m", "C_certificate.repro.fetch_pulses", "--n", "12"], cwd=RE_ROOT,
                           capture_output=True, text=True)
        last = json.loads(BEACON_CACHE.read_text())["pulses"][-1]["timeStamp"] if r.returncode == 0 else None
        tries.append({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "exit_code": r.returncode,
                      "last_pulse": last, "error": None if r.returncode == 0 else (r.stderr.strip().splitlines() or
                                                                                    ["?"])[-1]})
        if r.returncode != 0 or _iso(last) > _iso(ctx.get("commit_utc", "")):
            break
        print(f"    newest pulse {last} predates the commit; re-fetch in 30 s ({i + 1}/{FETCH_TRIES})")
        time.sleep(30)
    ctx["beacon_fetch"] = tries
    ctx["beacon_fetched"] = tries[-1]["exit_code"] == 0
    return {}


def _post_certify(ctx):
    cert = load(ctx["C.certificate"])
    if cert["status"] != "pass":
        raise StageFail(f"certificate status '{cert['status']}' (S = {cert.get('chsh_S')}): draw rejected and logged "
                        f"in C_certificate/runs/rejections.jsonl; no retry (epic decision 6)", code=2)
    ctx["seed"] = cert["extracted_seed_hex"]
    ctx["seed.A"] = f"{derive_seed(ctx['seed'], 'A.place'):016x}"
    acc = load(ctx["C.accounting"]) if ctx.get("C.accounting") else {}
    pulse_ts = (acc.get("pulse") or {}).get("timeStamp", "")
    after = bool(pulse_ts) and _iso(pulse_ts) > _iso(ctx.get("commit_utc", ""))
    ctx["beacon_fresh"] = bool(ctx.get("beacon_fetched")) and after
    ctx["beacon_pulse_time"] = pulse_ts
    out = []
    if not ctx["beacon_fresh"]:
        out.append(finding("weak-link", "warn", f"beacon pulse {pulse_ts or '?'} is not later than the commit "
                                                f"{ctx.get('commit_utc')} (or was not freshly fetched): the test-round "
                                                f"choice is not provably post-commit (beacon_fresh: false)", "C.certify"))
    here = (RE_ROOT / ctx["C.accounting"]).parent
    twins = [rel(p.parent) for p in (RE_ROOT / LETTERS["C"] / "runs").glob("*/certificate.json")
             if p.parent != here and json.loads(p.read_text()).get("extracted_seed_hex") == ctx["seed"]]
    if twins:
        out.append(finding("weak-link", "warn", f"extracted seed {ctx['seed'][:16]}… already produced by {', '.join(twins)}: "
                                                f"the simulated job is seeded from the public pulse, so reusing a pulse "
                                                f"reproduces the same 'certified' seed and the same tumour", "C.certify"))
    for f, ccr in (("beacon_pulse_id", "CCR-C3"), ("chsh_S_lower", "CCR-C2"), ("eps", "CCR-C2")):
        if f not in cert:
            out.append(finding("contract", "info", f"certificate lacks `{f}` ({ccr} unapplied)", "C.certify"))
    out.append(finding("weak-link", "info", "certify exits 0 on S ≤ 2; the runner gates on certificate.status",
                       "C.certify"))
    return out


def _a_cache(ctx) -> Path:
    return A_CACHE / ctx["host"] / "anatomy_masks.json"


def _skip_segment(ctx):
    return ("segmentation cache present", {"A.cache": _a_cache(ctx)}) if _a_cache(ctx).is_file() else None


def _probe_segment(ctx):
    root = Path(os.environ.get("LIDC_ROOT", Path.home() / "data" / "LIDC-IDRI"))
    out = []
    if not (root / ctx["host"]).is_dir():
        out.append(finding("precondition", "block", f"host DICOM {root / ctx['host']} not found", "A.segment"))
    if not _a_cache(ctx).is_file():
        out.append(finding("precondition", "warn", f"no segmentation cache for {ctx['host']}: TotalSegmentator + "
                                                   f"lungmask take ~25–75 min on CPU", "A.segment"))
    if not Path(ctx["python_a"]).is_file():
        out.append(finding("precondition", "block", f"A interpreter {ctx['python_a']} missing", "A.segment"))
    return out


def _probe_place(ctx):
    if list((RE_ROOT / LETTERS["A"] / "runs").glob("*-repro-proportions/proportions.json")):
        return []
    return [finding("gap", "info", "plan argv has no --radius-mm and place's fallback latest_radius() needs an A "
                                   "repro-proportions run (none on disk → SystemExit); runner passes --radius-mm",
                    "A.place")]


def _site(sites: dict, site_id: str) -> dict | None:
    return next((s for s in sites["sites"] if s["site_id"] == site_id), None)


def _post_draw(ctx):
    draw, sites = load(ctx["B.draw"]), load(ctx["A.sites"])
    site = _site(sites, draw["site_id"])
    if site is None:
        raise StageFail(f"contract mismatch: tumor_draw.site_id {draw['site_id']} is not in A's sites.json "
                        f"({len(sites['sites'])} sites); fix contract → producer → consumer")
    out = []
    if ctx["site_class"] == "auto":
        ctx["site_id"] = draw["site_id"]
    else:
        pick = next((s for s in sites["sites"] if s["context"]["placement_class"] == ctx["site_class"]), None)
        if pick is None:
            raise StageFail(f"no {ctx['site_class']} site in A's sites.json")
        ctx["site_id"] = pick["site_id"]
        if pick["site_id"] != draw["site_id"]:
            out.append(finding("weak-link", "warn", f"--site-class {ctx['site_class']} picks {pick['site_id']} but the "
                                                    f"draw says {draw['site_id']}: E marks its output stub:true and F "
                                                    f"raises on the site mismatch", "B.map"))
    c = site["context"]
    r_nom = c.get("nominal_radius_mm") or (c.get("extra") or {}).get("nominal_radius_mm")
    if r_nom and draw["size_mm"] / 2 > r_nom * 1.05:
        out.append(finding("weak-link", "warn", f"drawn {draw['type']} {draw['size_mm']} mm exceeds the "
                                                f"{c['placement_class']} site's nominal radius {r_nom} mm: the placement "
                                                f"class may no longer hold (B deferred this re-check)", "B.map"))
    if "nominal_radius_mm" not in c:
        out.append(finding("contract", "info", "site radius still in context.extra (CCR-A1 unapplied)", "A.place"))
    drift = json.dumps(load(ctx["B.drift"])) if ctx.get("B.drift") else ""
    if "pending" in drift:
        out.append(finding("gap", "warn", "B's drift.json still says the BP simulability number is pending D #9 "
                                          "(AC-9)", "B.map"))
    return out


def _post_grow_q(ctx):
    lin = load(ctx["D.lineage"])
    out = []
    if "founder_from" not in lin:
        out.append(finding("gap", "warn", "D's lineage ignores B's tumor_draw (fixed PHI0/DPHI, parent |1>): the "
                                          "founder is not derived from the draw (AC-8)", "D.grow"))
    wq = load(ctx["D.witness_qca"])
    if wq.get("passed") is False and wq.get("claim_level") == "L1":
        out.append(finding("contract", "warn", "QCA witness failed but witness_record says L1 (CCR-D4 unapplied)",
                           "D.grow"))
    shape = load(ctx["D.seed_shape"])
    out.append(finding("info", "info", f"seed_shape claim level {shape.get('claim_level')}", "D.grow"))
    return out


def _pre_grow_c(ctx):
    """AC-10: check E's lung HU bounds against the host's own lung-mask HU histogram."""
    import numpy as np
    import SimpleITK as sitk

    masks = load(ctx["A.masks"])
    base = (RE_ROOT / ctx["A.masks"]).parent
    ct = sitk.GetArrayFromImage(sitk.ReadImage(str(base / masks["files"]["host_ct"]["path"])))
    lungs = sitk.GetArrayFromImage(sitk.ReadImage(str(base / masks["files"]["lungs"]["path"]))) > 0
    hu = ct[lungs]
    params = json.loads(E_PARAMS.read_text())
    lo, hi = params["lung_hu_bounds"]
    p = dict(zip((1, 5, 50, 95, 99), np.percentile(hu, [1, 5, 50, 95, 99]).round(1).tolist()))
    inside = float(((hu >= lo) & (hu <= hi)).mean())
    ctx["lidc_hu_check"] = {"lung_hu_bounds": [lo, hi], "percentiles": p, "fraction_inside": round(inside, 3)}
    sev = "warn" if inside < 0.9 else "info"
    out = [finding("weak-link", sev, f"lung HU on {ctx['host']}: p1/p5/p50/p95/p99 = {list(p.values())}; "
                                     f"{inside:.1%} of lung voxels inside E's lung_hu_bounds [{lo}, {hi}]", "E.grow")]
    vt = {t: v.get("vessel_threshold") for t, v in params.get("types", {}).items()}
    out.append(finding("gap", "info", f"vessel_threshold {vt} is a push count (Pixel2Cancer), not HU: the plan's "
                                      f"'check against the HU histogram' does not apply to it", "E.grow"))
    return out


def _post_grow_c(ctx):
    tr = load(ctx["E.trajectory"])
    if tr.get("stub"):
        raise StageFail("growth_trajectory is stub:true: a real chain output was marked stub (site/draw mismatch?)")
    n = len(tr.get("snapshots", []))
    if n < 2:
        raise StageFail(f"growth_trajectory has {n} snapshot(s); baseline + follow-up needed")
    return [] if all("summary" in s for s in tr["snapshots"]) else [
        finding("contract", "info", "snapshots carry no summary (E CCR 1 unapplied; sidecar growth_summary.json)",
                "E.grow")]


def _probe_render(ctx):
    return [finding("weak-link", "warn", "`render --export` writes PNG slices into the git-tracked F_render/figures/: "
                                         "every chain run adds host-derived images to the repo", "F.render")]


def _post_render(ctx):
    import SimpleITK as sitk

    masks = load(ctx["A.masks"])
    host = sitk.ReadImage(str((RE_ROOT / ctx["A.masks"]).parent / masks["files"]["host_ct"]["path"]))
    hyb = sitk.ReadImage(str(RE_ROOT / ctx["F.hybrid_ct"]))
    for what in ("GetSpacing", "GetOrigin", "GetDirection"):
        a, b = getattr(host, what)(), getattr(hyb, what)()
        if any(abs(x - y) > 1e-4 for x, y in zip(a, b)) or host.GetSize() != hyb.GetSize():
            raise StageFail(f"hybrid not on A's host geometry: {what[3:].lower()} {b} vs host {a}")
    hv = load(ctx["F.hybrid"])
    return [] if "tumor_type" in hv else [
        finding("contract", "info", "hybrid_volume lacks tumor_type/size_mm (CCR-H3 unapplied)", "F.render")]


def _post_fill(ctx):
    rc = load(ctx["G.receipt"])
    n_passed = sum(1 for a in ctx.get("_argv_G.fill", []) if a == "--job")
    n_bound = len(rc["fill"]["job_ids"])
    if n_bound < n_passed:
        return [finding("gap", "warn", f"receipt binds {n_bound} of {n_passed} quantum jobs: `fill --job` keeps only "
                                       f"the last (B and D jobs unsigned)", "G.fill")]
    return []


def _post_verify(ctx):
    rep = load(ctx["G.verify"])
    ctx["verify_result"] = rep["verdict"]
    if rep["verdict"] != "VERIFIED":
        raise StageFail(f"receipt does not verify: {rep['verdict']}")
    return []


def _skip_lidc_ref(ctx):
    refs = sorted((RE_ROOT / LETTERS["H"] / "runs").glob("*-lidc-ref/lidc_ref.json"))
    return ("LIDC reference run present", {"H.lidc_ref": refs[-1].parent}) if refs else None


def _post_report(ctx):
    rep = load(ctx["H.report"])
    secs = rep.get("sections") or {k: v for k, v in rep.items() if isinstance(v, dict) and "needs" in v}
    thin = [k for k, v in secs.items() if isinstance(v, dict) and ("needs" in v or v.get("status") == "insufficient")]
    out = []
    if thin:
        out.append(finding("weak-link", "warn", f"H sections without a number at n = 1: {', '.join(thin)}", "H.report"))
    if "not powered" not in json.dumps(rep):
        out.append(finding("gap", "info", "H does not label n-dependent sections 'n=1 — not powered' (Q7)", "H.report"))
    return out


# ---------------------------------------------------------------------------------------------- the chain

ORDER = ["commit", "certify", "place", "draw", "grow_q", "grow_c", "render", "sign", "validate"]
PRIMARY = {"commit": "G.commit", "certify": "C.certify", "place": "A.place", "draw": "B.map", "grow_q": "D.grow",
           "grow_c": "E.grow", "render": "F.render", "sign": "G.fill", "validate": "H.report"}


def build(ctx: dict) -> dict[str, list[Step]]:
    from INT_integration.src import cohort, tamper_check

    R = Ref
    return {
        "commit": [
            Step("G.keys", "G", "G_provenance.src.keys", ["init"], run_dir=False, skip=_skip_keys, probe=_probe_keys),
            Step("G.commit", "G", "G_provenance.src.receipt", ["commit", "--rulebook", RULEBOOK],
                 outputs={"G.commit_receipt": "receipt.json", "G.commit_manifest": "commit_manifest.json"},
                 post=_post_commit, probe=_probe_commit),
        ],
        "certify": [
            Step("C.fetch", "C", "C_certificate.repro.fetch_pulses", ["--n", "12"], run_dir=False, optional=True,
                 func=_fetch_after_commit, probe=_probe_fetch),
            Step("C.certify", "C", "C_certificate.src.certify",
                 ["--mode", R("mode"), "--pulse-index", "-1", *ctx.get("certify_args", [])],
                 outputs={"C.certificate": "certificate.json", "C.qjr": "quantum_job_record.json",
                          "C.accounting": "accounting.json"}, post=_post_certify),
        ],
        "place": [
            Step("A.segment", "A", "A_placement.src.segment", ["--patient", R("host")], run_dir=False,
                 skip=_skip_segment, probe=_probe_segment),
            Step("A.place", "A", "A_placement.src.place",
                 ["--patient", R("host"), "--per-class", "10", "--seed-hex", R("seed.A"), "--radius-mm", R("radius_mm")],
                 outputs={"A.sites": "sites.json", "A.masks": "anatomy_masks.json"}, probe=_probe_place),
        ],
        "draw": [
            Step("B.map", "B", "B_mapping.src.map",
                 ["--variant", "b2", "--mode", R("mode"), "--sites", R("A.sites"), "--certificate", R("C.certificate"),
                  "--k-sites", "8"],
                 outputs={"B.rulebook": "rulebook.json", "B.circuit": "compiled_circuit.json",
                          "B.qjr": "quantum_job_record.json", "B.draw": "tumor_draw.json", "B.drift": "drift.json"},
                 post=_post_draw),
        ],
        "grow_q": [
            Step("D.grow", "D", "D_quantum_growth.src.grow",
                 ["--mode", R("mode"), "--tumor-draw", R("B.draw"), "--certificate", R("C.certificate"),
                  "--compiled-circuit", R("B.circuit")],
                 outputs={"D.lineage": "quantum_lineage.json", "D.witness_lineage": "witness_record_lineage.json",
                          "D.witness_qca": "witness_record_qca.json", "D.memory": "memory_advantage_record.json",
                          "D.simulability": "simulability_report.json", "D.seed_shape": "seed_shape.json",
                          "D.qjr_lineage": "quantum_job_record_lineage.json",
                          "D.qjr_qmachine": "quantum_job_record_qmachine.json",
                          "D.qjr_qca": "quantum_job_record_qca.json"},
                 post=_post_grow_q),
            Step("D.bp_b", "D", "D_quantum_growth.src.bp", ["--circuit", R("B.circuit")],
                 outputs={"D.bp_b": "simulability_report.json"}, optional=True),
        ],
        "grow_c": [
            Step("E.grow", "E", "E_classical_growth.src.grow",
                 ["--masks", R("A.masks"), "--sites", R("A.sites"), "--site-id", R("site_id"), "--draw", R("B.draw"),
                  "--certificate", R("C.certificate"), "--seed-shape", R("D.seed_shape"), "--follow-up-days", "90"],
                 outputs={"E.trajectory": "growth_trajectory/growth_trajectory.json"},
                 pre=_pre_grow_c, post=_post_grow_c),
        ],
        "render": [
            Step("F.fingerprint", "F", "F_render.src.fingerprint", ["--masks", R("A.masks")],
                 outputs={"F.fingerprint": "scanner_fingerprint.json"}),
            Step("F.render", "F", "F_render.src.render",
                 ["--trajectory", R("E.trajectory"), "--masks", R("A.masks"), "--sites", R("A.sites"),
                  "--draw", R("B.draw"), "--certificate", R("C.certificate"), "--library", LIBRARY,
                  "--fingerprint", R("F.fingerprint"), "--export"],
                 outputs={"F.hybrid": "hybrid_volume.json", "F.hybrid_ct": "hybrid_ct.nii.gz"}, post=_post_render,
                 probe=_probe_render),
        ],
        "sign": [
            Step("G.fill", "G", "G_provenance.src.receipt",
                 ["fill", "--commit", R("G.commit_receipt"), "--job", R("C.qjr"), "--job", R("B.qjr"),
                  "--job", R("D.qjr_lineage"), "--job", R("D.qjr_qmachine"), "--job", R("D.qjr_qca"),
                  "--certificate", R("C.certificate"), "--witness", R("D.witness_lineage"),
                  "--witness", R("D.witness_qca"), "--draw", R("B.draw"), "--hybrid", R("F.hybrid")],
                 outputs={"G.receipt": "receipt.json"}, post=_post_fill),
            Step("G.dicom", "G", "G_provenance.src.dicom_export", [R("G.receipt")], outputs={"G.series": "series"}),
            Step("G.verify", "G", "G_provenance.src.verify",
                 [R("G.series"), "--trusted", "G_provenance/runs/keys/trusted_keys.json"],
                 outputs={"G.verify": "verify_report.json"}, post=_post_verify),
            Step("INT.tamper", "INT", func=tamper_check.run, run_dir=False, optional=True),
        ],
        "validate": [
            Step("INT.cohort", "INT", func=cohort.write, run_dir=False),
            Step("H.lidc_ref", "H", "H_analysis.src.lidc_ref", ["--scans", "all"], outputs={"H.lidc_ref": "."},
                 skip=_skip_lidc_ref),
            Step("H.report", "H", "H_analysis.src.report",
                 ["--cohort", R("INT.cohort"), "--lidc-ref", R("H.lidc_ref")],
                 outputs={"H.report": "validation_report.json", "H.report_detail": "report_detail.json"},
                 post=_post_report),
        ],
    }
