"""Aggregate LIDC-IDRI radiologist-rating counts (type x size_bin x margin). Counts only, no voxels."""
import argparse
import json
import warnings
from collections import Counter

import numpy as np

from shared import RE_ROOT

OUT = RE_ROOT / "B_mapping" / "data" / "lidc_counts.json"
SIZE_EDGES = [3.0, 6.0, 10.0, 20.0, 30.0]
SIZE_BINS = ["3-6", "6-10", "10-20", "20-30"]


def _pylidc():
    # pylidc 0.2.3 predates numpy 2 / python 3.12 removals
    import configparser
    if not hasattr(np, "int"):
        np.int = int
    if not hasattr(np, "bool"):
        np.bool = bool
    if not hasattr(np, "float"):
        np.float = float
    if not hasattr(configparser, "SafeConfigParser"):
        configparser.SafeConfigParser = configparser.ConfigParser
    import pylidc as pl
    return pl


def type_of(texture: float) -> str:
    if texture <= 2:
        return "ground-glass"
    if texture <= 3:
        return "part-solid"
    return "solid"


def margin_of(spiculation: float, lobulation: float) -> str:
    if spiculation >= 3:
        return "spiculated"
    if lobulation >= 3:
        return "lobulated"
    return "smooth"


def size_bin_of(d: float):
    for lo, hi, name in zip(SIZE_EDGES[:-1], SIZE_EDGES[1:], SIZE_BINS):
        if lo <= d < hi:
            return name
    return None


def collect():
    warnings.filterwarnings("ignore")
    pl = _pylidc()
    counts = Counter()
    n_nod = n_drop = 0
    for scan in pl.query(pl.Scan).all():
        for anns in scan.cluster_annotations(verbose=False):
            n_nod += 1
            d = float(np.median([a.diameter for a in anns]))
            sb = size_bin_of(d)
            if sb is None:
                n_drop += 1
                continue
            t = type_of(float(np.median([a.texture for a in anns])))
            m = margin_of(float(np.median([a.spiculation for a in anns])),
                          float(np.median([a.lobulation for a in anns])))
            counts[(t, sb, m)] += 1
    return counts, n_nod, n_drop


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    counts, n_nod, n_drop = collect()
    doc = {
        "source": "LIDC-IDRI via pylidc 0.2.3, radiologist ratings, median per nodule cluster",
        "mapping": {
            "type": "median texture 1-2 ground-glass, 3 part-solid, 4-5 solid",
            "margin": "median spiculation>=3 spiculated, else median lobulation>=3 lobulated, else smooth",
            "size": "median annotation diameter; <3 mm or >30 mm dropped",
        },
        "n_nodules_clustered": n_nod,
        "n_dropped_size": n_drop,
        "n_used": sum(counts.values()),
        "size_bins": SIZE_BINS,
        "counts": [{"type": t, "size_bin": s, "margin": m, "n": n} for (t, s, m), n in sorted(counts.items())],
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n")
    by_type = Counter()
    for (t, _, _), n in counts.items():
        by_type[t] += n
    print(f"wrote {OUT.relative_to(RE_ROOT)}: used {doc['n_used']}/{n_nod}; by type {dict(by_type)}")


if __name__ == "__main__":
    main()
