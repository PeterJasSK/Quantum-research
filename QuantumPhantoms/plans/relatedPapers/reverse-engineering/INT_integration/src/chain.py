"""INT chain runner: one tumour A→H from real contract files, each letter called through its own CLI.

    python -m INT_integration.src.chain --host LIDC-IDRI-0004 --probe             # find gaps, run nothing
    python -m INT_integration.src.chain --host LIDC-IDRI-0004 --dry-run           # print every step's command
    python -m INT_integration.src.chain --host LIDC-IDRI-0004 --mode heron --tag ref
    python -m INT_integration.src.chain ... --stop-after certify                  # run only a prefix
    python -m INT_integration.src.chain ... --from render --resume runs/<chain> [--reuse A.place=<run dir> …]

Stages: commit → certify → place → draw → grow_q → grow_c → render → sign → validate. Each step is a subprocess
(A with the qp-re-a interpreter), its new <letter>/runs/* dir is found by --tag or as the single new directory,
its contract outputs are validated with shared.validate, and its checks add findings to runs/<chain>/chain.json
(written after every step, so a stopped chain can be resumed). A failure stops the chain; no retries.

--probe runs nothing: it asks every letter's argparse (--help) whether the flags the plan's chain passes exist,
checks preconditions, and writes runs/<ts>-probe-<tag>/probe.{json,md}. Exit 4 when a step is blocked by a gap.
A real run stops at the same gaps; --allow-gaps runs past them (still recorded) to find what breaks next.

Exit codes: 0 ok, 1 stage failure, 2 certificate fail (S ≤ 2), 3 code changed after commit / reuse refused,
4 blocked by an integration gap.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from shared import LETTERS, RE_ROOT
from shared.validate import validate_file
from INT_integration.src.stages import (NON_RUN_DIRS, ORDER, PRIMARY, StageFail, Step, build, cli_findings, cli_help,
                                        finding, letter_code_hash, rel, resolve_args)

PYTHON_A = "/home/peter/anaconda3/envs/qp-re-a/bin/python"
CHAIN_RUNS = RE_ROOT / "runs"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_dirs(step: Step) -> set[str]:
    d = step.folder / "runs"
    return {p.name for p in d.iterdir() if p.is_dir() and p.name not in NON_RUN_DIRS} if d.is_dir() else set()


def _collect(step: Step, run_dir: Path) -> dict:
    out = {}
    for key, name in step.outputs.items():
        p = run_dir / name
        if not p.exists():
            raise StageFail(f"{step.name}: expected output {rel(p)} was not written")
        out[key] = rel(p)
    return out


def _validate(outputs: dict) -> list[str]:
    errs = []
    for key, p in outputs.items():
        f = RE_ROOT / p
        if f.suffix not in (".json", ".jsonl") or not f.is_file():
            continue
        if f.suffix == ".json" and "contract" not in json.loads(f.read_text()):
            continue
        _, e = validate_file(f)
        errs += [f"{key} ({p}): {x}" for x in e]
    return errs


def _code_freeze(step: Step, ctx: dict) -> None:
    """Any letter edit after `commit` invalidates the chain (G checks the same hashes at fill)."""
    want = ctx.get("code_hashes", {}).get(step.letter)
    if want and letter_code_hash(step.letter) != want:
        raise StageFail(f"{LETTERS[step.letter]} code changed after the commit ({ctx.get('commit_utc')}): "
                        f"rerun the chain from commit", code=3)


def _check_reuse(step: Step, run_dir: Path, ctx: dict) -> None:
    rr = json.loads((run_dir / "run.json").read_text())
    if "commit_utc" in ctx and rr["created_utc"] < ctx["commit_utc"]:
        raise StageFail(f"--reuse {step.name}={rel(run_dir)} refused: created {rr['created_utc']} before the commit "
                        f"{ctx['commit_utc']} (G's ordering rule)", code=3)
    committed = ctx.get("code_hashes", {}).get(step.letter)
    if committed and rr["code_hash"] != committed:
        raise StageFail(f"--reuse {step.name}={rel(run_dir)} refused: produced by code {rr['code_hash'][:12]}…, "
                        f"not the committed {committed[:12]}…", code=3)


class Chain:
    def __init__(self, a: argparse.Namespace):
        self.a = a
        self.ctx: dict = {"host": a.host, "mode": a.mode, "site_class": a.site_class, "radius_mm": str(a.radius_mm),
                          "python": a.python, "python_a": a.python_a, "certify_args": shlex.split(a.certify_args)}
        self.records: list[dict] = []
        self.findings: list[dict] = []
        self.reuse = dict(r.split("=", 1) for r in a.reuse)
        self.reuse = {PRIMARY.get(k, k): v for k, v in self.reuse.items()}
        if a.resume:
            prev = json.loads((Path(a.resume) / "chain.json").read_text())
            self.ctx.update({k: v for k, v in prev["ctx"].items() if k not in self.ctx or k == "certify_args"})
            keep = set(ORDER[:ORDER.index(a.from_)])
            self.records = [r for r in prev["stages"] if r["stage"] in keep]
            self.findings = [f for f in prev["findings"] if f.get("stage") in keep]
        self.stages = build(self.ctx)

    def selected(self) -> list[str]:
        lo, hi = ORDER.index(self.a.from_), ORDER.index(self.a.stop_after)
        return ORDER[lo:hi + 1]

    # ------------------------------------------------------------------------------------- dry run / probe

    def dry_run(self) -> int:
        for stage in self.selected():
            print(f"\n[{stage}]")
            for s in self.stages[stage]:
                if not s.module:
                    print(f"  {s.name:<15} (runner-local: {s.func.__module__}.{s.func.__name__})")
                    continue
                py = "$PY_A" if s.letter == "A" else "$PY"
                print(f"  {s.name:<15} {py} -m {s.module} {shlex.join(resolve_args(s, self.ctx, strict=False))}")
        print("\n$PY = " + self.ctx["python"] + "\n$PY_A = " + self.ctx["python_a"])
        return 0

    def probe(self) -> int:
        rows = []
        helps: dict = {}
        for stage in self.selected():
            for s in self.stages[stage]:
                fs = []
                if s.module:
                    py = s.interpreter(self.ctx)
                    key = (py, s.module, tuple(s.subcommand()))
                    if key not in helps:
                        print(f"  probing {s.name} …", file=sys.stderr)
                        helps[key] = cli_help(py, s)
                    fs += cli_findings(s, helps[key])
                    if s.run_dir and helps[key].get("ok") and "--tag" not in helps[key]["flags"]:
                        fs.append(finding("gap", "info", "no --tag: run dir found as the single new runs/* dir", s.name))
                if s.probe:
                    fs += s.probe(self.ctx)
                for f in fs:
                    f.setdefault("stage", stage)
                    f["step"] = f["step"] or s.name
                worst = "block" if any(f["severity"] == "block" for f in fs) else \
                        "warn" if any(f["severity"] == "warn" for f in fs) else "ok"
                argv = None if not s.module else [s.module, *resolve_args(s, self.ctx, strict=False)]
                rows.append({"stage": stage, "step": s.name, "optional": s.optional, "status": worst, "argv": argv,
                             "findings": fs})
        out = CHAIN_RUNS / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-probe-{self.a.tag}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "probe.json").write_text(json.dumps({"host": self.a.host, "mode": self.a.mode, "probed_utc": _utc(),
                                                    "steps": rows}, indent=2, ensure_ascii=False) + "\n")
        md = ["| Stage | Step | Status | Finding |", "|---|---|---|---|"]
        for r in rows:
            label = r["status"] + (" (optional)" if r["optional"] else "")
            if not r["findings"]:
                md.append(f"| {r['stage']} | {r['step']} | {label} | — |")
            for f in r["findings"]:
                md.append(f"| {r['stage']} | {r['step']} | {label} | {f['severity']} · {f['kind']}: {f['msg']} |")
        (out / "probe.md").write_text("\n".join(md) + "\n")
        print("\n".join(md))
        blocked = [r["step"] for r in rows if r["status"] == "block" and not r["optional"]]
        print(f"\nprobe → {rel(out)}/probe.md; blocked steps: {', '.join(blocked) or 'none'}")
        return 4 if blocked else 0

    # ------------------------------------------------------------------------------------- run

    def save(self, status: str, code: int | None = None) -> None:
        doc = {"chain_id": self.dir.name, "host": self.a.host, "mode": self.a.mode, "site_class": self.a.site_class,
               "status": status, "exit_code": code, "beacon_fresh": self.ctx.get("beacon_fresh"),
               "commit_receipt": self.ctx.get("G.commit_receipt"), "commit_utc": self.ctx.get("commit_utc"),
               "stages": self.records, "verify_result": self.ctx.get("verify_result"),
               "tamper_check": self.ctx.get("tamper_check"), "validation_report": self.ctx.get("H.report"),
               "beacon_fetch": self.ctx.get("beacon_fetch"), "lidc_hu_check": self.ctx.get("lidc_hu_check"),
               "mismatches": [f for f in self.findings if f["kind"] == "contract"],
               "findings": self.findings, "ctx": {k: v for k, v in self.ctx.items() if not k.startswith("_")}}
        (self.dir / "chain.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str) + "\n")

    def note(self, stage: str, fs: list[dict]) -> None:
        for f in fs:
            f["stage"] = stage
            self.findings.append(f)
            if f["severity"] != "info":
                print(f"    ! {f['severity']} · {f['kind']}: {f['msg']}")

    def step(self, stage: str, s: Step) -> None:
        rec = {"stage": stage, "step": s.name, "argv": None, "interpreter": None, "run_dir": None, "outputs": {},
               "exit_code": None, "started_utc": _utc(), "finished_utc": None, "status": "running"}
        self.records.append(rec)
        print(f"  {s.name}")
        try:
            if s.name in self.reuse:
                run_dir = RE_ROOT / self.reuse[s.name]
                _check_reuse(s, run_dir, self.ctx)
                rec.update(status="reused", run_dir=rel(run_dir), outputs=_collect(s, run_dir))
            elif s.skip and (hit := s.skip(self.ctx)):
                rec.update(status="cached", note=hit[0], outputs={k: rel(v) for k, v in hit[1].items()})
            elif s.func:
                if s.pre:
                    self.note(stage, s.pre(self.ctx))
                rec["outputs"] = s.func(self.ctx, self.dir)
                rec["status"] = "ok"
            else:
                self.run_cli(stage, s, rec)
            self.ctx.update(rec["outputs"])
            if rec["status"] in ("ok", "reused") and s.post:
                self.note(stage, s.post(self.ctx))
        except StageFail as e:
            rec.update(status="blocked-gap" if rec["status"] == "blocked-gap" else "failed", error=str(e),
                       finished_utc=_utc())
            if not s.optional:
                raise
            self.note(stage, [finding("gap", "warn", str(e), s.name)])
        rec["finished_utc"] = rec["finished_utc"] or _utc()
        self.save("running")

    def run_cli(self, stage: str, s: Step, rec: dict) -> None:
        help_ = cli_help(s.interpreter(self.ctx), s)
        gaps = cli_findings(s, help_)
        self.note(stage, gaps)
        if any(f["severity"] in ("block", "warn") and f["kind"] == "gap" for f in gaps) and not self.a.allow_gaps:
            rec["status"] = "blocked-gap"
            raise StageFail(f"{s.name} blocked by integration gap(s): " + "; ".join(f["msg"] for f in gaps), code=4)
        if s.letter in LETTERS:
            _code_freeze(s, self.ctx)
        if s.pre:
            self.note(stage, s.pre(self.ctx))
        argv = resolve_args(s, self.ctx)
        if "--tag" in help_["flags"]:
            argv += ["--tag", f"int-{self.a.tag}"]
        self.ctx[f"_argv_{s.name}"] = argv
        cmd = [s.interpreter(self.ctx), "-m", s.module, *argv]
        rec.update(argv=cmd[2:], interpreter=cmd[0])
        before = _run_dirs(s)
        logs = self.dir / "logs"
        logs.mkdir(exist_ok=True)
        with open(logs / f"{s.name}.log", "w") as log:
            r = subprocess.run(cmd, cwd=RE_ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
        rec["exit_code"] = r.returncode
        if r.returncode != 0:
            tail = (logs / f"{s.name}.log").read_text().strip().splitlines()[-1:] or [""]
            raise StageFail(f"{s.name} exited {r.returncode}: {tail[0]} (log: {rel(logs / (s.name + '.log'))})",
                            code=r.returncode if r.returncode in (2, 3) else 1)
        if s.run_dir:
            new = sorted(_run_dirs(s) - before)
            if len(new) != 1:
                raise StageFail(f"{s.name}: expected 1 new run dir in {rel(s.folder / 'runs')}, found {len(new)}")
            run_dir = s.folder / "runs" / new[0]
            rec["run_dir"] = rel(run_dir)
            rec["outputs"] = _collect(s, run_dir)
            errs = _validate(rec["outputs"])
            if errs:
                self.note(stage, [finding("contract", "block", e, s.name) for e in errs])
                raise StageFail(f"{s.name}: outputs violate their contracts ({len(errs)} error(s))")
        rec["status"] = "ok"

    def run(self) -> int:
        self.dir = CHAIN_RUNS / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-e2e-{self.a.tag}"
        self.dir.mkdir(parents=True)
        print(f"chain {rel(self.dir)}  host {self.a.host}  mode {self.a.mode}  stages {', '.join(self.selected())}")
        try:
            for stage in self.selected():
                print(f"[{stage}]")
                for s in self.stages[stage]:
                    self.step(stage, s)
        except StageFail as e:
            print(f"STOP: {e}", file=sys.stderr)
            self.note(self.records[-1]["stage"] if self.records else "", [finding("info", "info", f"stopped: {e}")])
            self.save("stopped", e.code)
            return e.code
        done = self.selected()[-1] == ORDER[-1]
        self.save("complete" if done else f"stopped after {self.selected()[-1]}", 0)
        n = {s: sum(f["severity"] == s for f in self.findings) for s in ("block", "warn", "info")}
        print(f"done → {rel(self.dir)}/chain.json  findings: {n['block']} block, {n['warn']} warn, {n['info']} info")
        return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m INT_integration.src.chain", description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="LIDC-IDRI-0004")
    ap.add_argument("--mode", choices=("heron", "ideal"), default="heron")
    ap.add_argument("--site-class", choices=("auto", "free", "juxtavascular", "juxtapleural"), default="auto")
    ap.add_argument("--from", dest="from_", choices=ORDER, default=ORDER[0])
    ap.add_argument("--stop-after", choices=ORDER, default=ORDER[-1])
    ap.add_argument("--reuse", action="append", default=[], metavar="STEP=RUN_DIR",
                    help="stage or step name (e.g. place, A.place) = an existing run dir (must postdate the commit)")
    ap.add_argument("--resume", metavar="CHAIN_DIR", help="take ctx and records of stages before --from from here")
    ap.add_argument("--tag", default="ref")
    ap.add_argument("--radius-mm", type=float, default=4.72, help="A's nominal lesion radius (reference run r)")
    ap.add_argument("--certify-args", default="", help='extra C certify args, e.g. "--settings classical"')
    ap.add_argument("--allow-gaps", action="store_true",
                    help="run a step despite gaps (recorded); a missing flag still fails in the letter's argparse")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--python-a", default=PYTHON_A)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="print every step's command; run nothing")
    mode.add_argument("--probe", action="store_true", help="find integration gaps and preconditions; run nothing")
    a = ap.parse_args(argv)
    if ORDER.index(a.from_) > ORDER.index(a.stop_after):
        ap.error("--from is after --stop-after")
    if a.from_ != ORDER[0] and not a.resume and not a.dry_run and not a.probe:
        ap.error("--from needs --resume <chain dir> (earlier stages' outputs)")
    c = Chain(a)
    if a.dry_run:
        return c.dry_run()
    if a.probe:
        return c.probe()
    return c.run()


if __name__ == "__main__":
    sys.exit(main())
