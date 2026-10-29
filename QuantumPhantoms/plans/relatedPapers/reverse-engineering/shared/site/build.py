"""Static, offline site build: Markdown + per-letter status.json → index.html + site/.

    python -m shared.site.build                  # preview (letters: never commit index.html / site/)
    python -m shared.site.build --update-readme  # also rewrite the STATUS block in README.md (W / INT only)

Steps: validate every status.json and the 21-target set (abort on error) → render letter READMEs,
dossiers, the shared docs, future.md and INT_integration/README.md with markdown-it-py through jinja2 → rewrite relative
links (.md → .html, anything else → the source file) → copy figures/ → write index.html, site/**, site/style.css.
INT: each letter README's `<!-- readiness: … -->` marker becomes a rating badge (missing → warning, "unrated");
pipeline-overview.md's `<!-- weak-edges: X>Y, … -->` marker highlights diagram edges (its text is not rendered). No network, no CDN, no scripts.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from html import unescape
from urllib.parse import quote, unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

from shared import LETTERS, RE_ROOT, SHARED
from shared.validate import check_status_set

HERE = Path(__file__).resolve().parent
SITE = RE_ROOT / "site"
INDEX = RE_ROOT / "index.html"
README = RE_ROOT / "README.md"
OVERVIEW = RE_ROOT / "pipeline-overview.md"
FUTURE = RE_ROOT / "future.md"
INT_README = RE_ROOT / "INT_integration" / "README.md"
SHARED_DOCS = [SHARED / "README.md", SHARED / "contracts" / "README.md", SHARED / "contracts" / "VOLUMES.md",
               SHARED / "stubs" / "README.md"]
STATES = ["listed", "dissected", "reproduced", "adapted", "integrated", "rejected"]
STATUS_BEGIN, STATUS_END = "<!-- STATUS:BEGIN -->", "<!-- STATUS:END -->"
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_EXTERNAL_ASSET = re.compile(r"<(script|link|img)\b[^>]*\b(src|href)=\"(https?:)?//", re.I)
READINESS = {"not-ready": "Not ready", "prototype": "Prototype", "caveats": "Usable with caveats",
             "production": "Production-ready"}
STEP = {"A": "Where a tumour sits", "B": "What kind of tumour", "C": "How it is certified", "D": "How it grows (quantum)",
        "E": "How it grows (tissue)", "F": "How it looks on CT", "G": "How it is traced", "H": "How it is validated"}
# Images to show per step on the index ("See each step"): (figure file, caption, kind). kind: ct = real LIDC CT
# pixels, phantom = synthetic/stub volume, plot = chart. Best showable image first.
GALLERY = {
    "A": [("18-host-sites.png", "Anatomy masks and candidate sites on a real chest CT (LIDC-IDRI-0004)", "ct"),
          ("18-class-proportions.png", "Placement-class proportions vs the paper", "plot")],
    "B": [("drift_b1_b2.png", "Tumour draws: ideal vs Heron-class noise", "plot"),
          ("qemcmc_tumor_gap.png", "Quantum-enhanced MCMC on a tumour energy landscape", "plot")],
    "C": [("hmin_vs_S.png", "Bell value S → certified entropy per round", "plot"),
          ("beacon_chain.png", "Public beacon chain verified pulse by pulse", "plot")],
    "D": [("qca_snapshot_2d.png", "Quantum cellular automaton → 3-D tumour seed shape", "phantom"),
          ("lineage_witness.png", "Cell-lineage entanglement witness per generation", "plot"),
          ("cellcycle_memory_advantage.png", "Quantum memory advantage for cell-division timing", "plot")],
    "E": [("lung_S002.png", "Tumour growth, baseline → follow-up, against a vessel (lung masks, stub host)", "phantom"),
          ("kt_cross_sections.png", "Layered tumour: proliferating rim, dormant shell, necrotic core", "phantom"),
          ("lung_growth_curves.png", "Growth curves per tumour type", "plot")],
    "F": [("render-lidc0001-lung.png", "Synthetic nodule inserted into a real chest CT (LIDC-IDRI-0001), lung window", "ct"),
          ("render-lidc0001-mediastinal.png", "Same nodule, mediastinal window", "ct"),
          ("r15-peng-patch-noise.png", "Scanner-matched noise", "phantom")],
    "G": [("r19-ctgan-tamper.png", "Injected / removed tumour caught by the signature, slice by slice", "phantom")],
    "H": [("r20a_cho_vs_ideal.png", "Model observer checked against the ideal observer", "plot"),
          ("r20b_mrmc_se.png", "Reader-study variance (MRMC)", "plot")],
}
KIND_LABEL = {"ct": "real CT", "phantom": "phantom", "plot": "plot"}
_READY = re.compile(r"<!--\s*readiness:\s*([\w-]+)\s*-->")
_WEAK = re.compile(r"<!--\s*weak-edges:\s*(.*?)\s*-->")
_HEADING = re.compile(r"<h([23])>(.*?)</h\1>")


def _out_path(src: Path) -> Path:
    rel = src.relative_to(RE_ROOT)
    name = "index.html" if rel.name == "README.md" else rel.with_suffix(".html").name
    return SITE / rel.parent / name


def _title(md_text: str, fallback: str) -> str:
    m = re.search(r"^# (.+)$", md_text, re.M)
    return m.group(1).strip() if m else fallback


def _stars(n: int) -> str:
    return "★" * n


def _readiness(md_text: str) -> str | None:
    m = _READY.search(md_text)
    return m.group(1) if m and m.group(1) in READINESS else None


def _slug(html: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", "", html)).lower()
    return re.sub(r"[^\w]+", "-", text).strip("-")


def _anchor(html: str) -> str:
    """Give h2/h3 an id (GitHub-style slug) so `README.md#pipeline-readiness` links resolve on the site."""
    return _HEADING.sub(lambda m: f'<h{m.group(1)} id="{_slug(m.group(2))}">{m.group(2)}</h{m.group(1)}>', html)


def _badge(r: str | None) -> str:
    r = r or "unrated"
    return f'<span class="badge ready-{r}">{READINESS.get(r, "unrated")}</span>'


class Builder:
    def __init__(self, statuses: dict):
        self.statuses = statuses
        self.md = MarkdownIt("commonmark", {"html": True}).enable("table")
        self.env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["j2"]),
                               keep_trailing_newline=True)
        self.env.filters["stars"] = _stars
        self.sources: list[Path] = []
        for folder in LETTERS.values():
            self.sources.append(RE_ROOT / folder / "README.md")
            self.sources += sorted((RE_ROOT / folder / "dossiers").glob("*.md"))
        self.sources += [p for p in SHARED_DOCS if p.is_file()]
        self.sources += [p for p in (FUTURE, INT_README) if p.is_file()]
        self.pages = {p.resolve(): _out_path(p) for p in self.sources}
        self.pages[README.resolve()] = INDEX
        self.pages[OVERVIEW.resolve()] = INDEX
        self.assets: dict[Path, Path] = {}
        self.dossier_target = {}
        for letter, st in statuses.items():
            folder = RE_ROOT / LETTERS[letter]
            for t in st["targets"]:
                self.dossier_target[(folder / t["dossier"]).resolve()] = (letter, t)
        self.letters = [{"letter": L, "folder": f, "title": self._letter_title(L), "step": STEP[L],
                         "readiness": self._letter_ready(f)}
                        for L, f in LETTERS.items()]
        self.warnings = [f"{x['folder']}/README.md: no readiness marker (shown as unrated)"
                         for x in self.letters if not x["readiness"]]

    def _letter_title(self, letter: str) -> str:
        readme = RE_ROOT / LETTERS[letter] / "README.md"
        title = _title(readme.read_text(), LETTERS[letter]) if readme.is_file() else LETTERS[letter]
        return title.split("—", 1)[-1].strip()

    @staticmethod
    def _letter_ready(folder: str) -> str | None:
        readme = RE_ROOT / folder / "README.md"
        return _readiness(readme.read_text()) if readme.is_file() else None

    def _rewrite(self, url: str, src: Path, out: Path) -> str:
        if not url or url.startswith(("#", "/")) or _SCHEME.match(url):
            return url
        path, _, frag = url.partition("#")
        target = (src.parent / unquote(path)).resolve()
        if target.is_dir() and (target / "README.md").resolve() in self.pages:
            target = (target / "README.md").resolve()
        dest = self.pages.get(target) or self.assets.get(target) or target
        rel = os.path.relpath(dest, out.parent)
        return quote(Path(rel).as_posix()) + (f"#{frag}" if frag else "")

    def _render_md(self, src: Path, out: Path) -> str:
        tokens = self.md.parse(src.read_text())
        for tok in tokens:
            for child in tok.children or []:
                attr = "href" if child.type == "link_open" else "src" if child.type == "image" else None
                if attr:
                    child.attrSet(attr, self._rewrite(child.attrGet(attr) or "", src, out))
        html = self.md.renderer.render(tokens, self.md.options, {})
        return _anchor(_READY.sub(lambda m: _badge(m.group(1) if m.group(1) in READINESS else None), html))

    def _root(self, out: Path) -> str:
        rel = os.path.relpath(RE_ROOT, out.parent)
        return "" if rel == "." else Path(rel).as_posix() + "/"

    def _write(self, out: Path, template: str, **ctx) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        html = self.env.get_template(template).render(root=self._root(out), letters=self.letters, **ctx)
        bad = _EXTERNAL_ASSET.search(html)
        if bad:
            raise SystemExit(f"external asset in {out}: {bad.group(0)}")
        out.write_text(html)

    def copy_figures(self) -> None:
        for folder in LETTERS.values():
            figs = RE_ROOT / folder / "figures"
            for f in sorted(figs.rglob("*")) if figs.is_dir() else []:
                if f.is_file() and f.name != ".gitkeep":
                    dest = SITE / folder / "figures" / f.relative_to(figs)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(f, dest)
                    self.assets[f.resolve()] = dest

    def targets(self) -> list[dict]:
        rows = []
        for letter, st in self.statuses.items():
            for t in st["targets"]:
                page = self.pages[(RE_ROOT / LETTERS[letter] / t["dossier"]).resolve()]
                rows.append({**t, "letter": letter, "folder": LETTERS[letter],
                             "href": page.relative_to(RE_ROOT).as_posix(),
                             "reproduced_text": self._reproduced_text(t)})
        return sorted(rows, key=lambda r: r["number"])

    @staticmethod
    def _reproduced_text(t: dict) -> str:
        r = t.get("reproduced")
        if not r:
            return "—"
        unit = f" {r['unit']}" if r.get("unit") else ""
        return f"{r['our_value']}{unit} vs paper {r['paper_value']}{unit} ({r['agreement']})"

    def build(self) -> int:
        if SITE.exists():
            shutil.rmtree(SITE)
        SITE.mkdir()
        shutil.copyfile(HERE / "style.css", SITE / "style.css")
        self.copy_figures()
        rows = self.targets()
        for src in self.sources:
            out = self.pages[src.resolve()]
            text = src.read_text()
            letter_info = target = None
            if src.resolve() in self.dossier_target:
                letter, target = self.dossier_target[src.resolve()]
                letter_info = next(x for x in self.letters if x["letter"] == letter)
            elif src.name == "README.md" and src.parent.name in LETTERS.values():
                letter_info = next(x for x in self.letters if x["folder"] == src.parent.name)
            letter_rows = [r for r in rows if letter_info and r["letter"] == letter_info["letter"]] if not target else []
            self._write(out, "page.html.j2", title=_title(text, src.stem), body=self._render_md(src, out),
                        source=src.relative_to(RE_ROOT).as_posix(), target=target, letter=letter_info,
                        letter_rows=letter_rows)
        cards = []
        for L in self.letters:
            mine = [r for r in rows if r["letter"] == L["letter"]]
            cards.append({**L, "n": len(mine), "counts": {s: sum(r["state"] == s for r in mine) for s in STATES}})
        totals = {s: sum(r["state"] == s for r in rows) for s in STATES}
        weak = []
        if OVERVIEW.is_file():
            m = _WEAK.search(OVERVIEW.read_text())
            weak = [e.strip() for e in m.group(1).split(",") if e.strip()] if m else []
        ready = {L["letter"]: L["readiness"] or "unrated" for L in self.letters}
        gallery = []
        for L in self.letters:
            items = []
            for name, caption, kind in GALLERY.get(L["letter"], []):
                src = RE_ROOT / L["folder"] / "figures" / name
                if not src.is_file():
                    self.warnings.append(f"gallery: {src.relative_to(RE_ROOT)} missing")
                    continue
                items.append({"href": f"site/{L['folder']}/figures/{name}", "caption": caption, "kind": kind,
                              "kind_label": KIND_LABEL[kind]})
            gallery.append({**L, "items": items})
        self._write(INDEX, "index.html.j2", title="Index", cards=cards, rows=rows, states=STATES, totals=totals,
                    weak_edges=weak, gallery=gallery, ready=ready, ready_labels=READINESS)
        return len(self.sources) + 1


def status_table_md(rows: list[dict]) -> str:
    lines = ["| # | Letter | Target | Priority | Kind | State | Claim | Reproduced |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['number']} | {r['letter']} | [{r['name']}]({r['folder']}/{r['dossier']}) | {_stars(r['priority'])} "
                     f"| {r['kind']} | {r['state']} | {r['claim_level'] or '—'} | {r['reproduced_text']} |")
    return "\n".join(lines)


def update_readme(rows: list[dict]) -> None:
    text = README.read_text()
    if STATUS_BEGIN not in text or STATUS_END not in text:
        raise SystemExit(f"{README}: STATUS markers not found")
    head, rest = text.split(STATUS_BEGIN, 1)
    _, tail = rest.split(STATUS_END, 1)
    README.write_text(f"{head}{STATUS_BEGIN}\n<!-- generated by `python -m shared.site.build --update-readme`; "
                      f"do not edit by hand -->\n{status_table_md(rows)}\n{STATUS_END}{tail}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m shared.site.build", description=__doc__.split("\n")[0])
    ap.add_argument("--update-readme", action="store_true", help="rewrite README.md STATUS block (W / INT only)")
    a = ap.parse_args(argv)
    statuses, errs = check_status_set()
    if errs:
        print("site build aborted: status validation failed", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 1
    b = Builder(statuses)
    n = b.build()
    for w in b.warnings:
        print(f"warning: {w}", file=sys.stderr)
    if a.update_readme:
        update_readme(b.targets())
    rows = b.targets()
    print(f"built {n} pages ({len(rows)} targets: "
          + ", ".join(f"{sum(r['state'] == s for r in rows)} {s}" for s in STATES if any(r['state'] == s for r in rows))
          + f") → {INDEX.relative_to(RE_ROOT)}, {SITE.relative_to(RE_ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
