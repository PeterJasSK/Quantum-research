"""`utility` section: train-synthetic / test-real with the 3-D CHO and MRMC delta-AUC.

Task: lesion-known-exactly detection, nodule present vs absent, 48^3 mm ROIs at 1 mm. Arm S trains on synthetic
positives (hybrid ROIs) vs negatives from the same hosts; arm R trains on real positives from training patients.
Both arms are tested on the same held-out real positives + negatives (patient-disjoint).
"""
from __future__ import annotations

import numpy as np

from H_analysis.src import mrmc, observer
from shared import seedhash

N_READERS_DEFAULT = 30
N_TRAIN = 100
VICTRE_HETERO = {"pos": 2000, "neg": 1500}


def _readers(train_pos, train_neg, test_pos, test_neg, chans, n_readers, n_train, seed_hex, tag):
    """-> (scores_neg (R,Nn), scores_pos (R,Np)): each reader trains on its own resampled pairs; same test set."""
    vtp = observer.channel_outputs(train_pos, chans)
    vtn = observer.channel_outputs(train_neg, chans)
    sp = observer.channel_outputs(test_pos, chans)
    sn = observer.channel_outputs(test_neg, chans)
    out_p, out_n = [], []
    for k in range(n_readers):
        r = seedhash.rng(seed_hex, f"H.reader.{k}.{tag}")
        ip = r.choice(len(vtp), n_train, replace=len(vtp) < n_train)
        ineg = r.choice(len(vtn), n_train, replace=len(vtn) < n_train)
        w = observer.cho_train_v(vtp[ip], vtn[ineg])
        out_p.append(sp @ w)
        out_n.append(sn @ w)
    return np.array(out_n), np.array(out_p)


def run(syn_pos, syn_neg, real_train_pos, real_train_neg, test_pos, test_neg, test_pos_types, d_eq_mm,
        seed_hex: str, n_readers: int = N_READERS_DEFAULT) -> dict:
    n_pos, n_neg = len(test_pos), len(test_neg)
    base = {"task": "LKE detection 3-D", "observer": "CHO-LG3D", "n_readers": n_readers,
            "n_test": {"pos": n_pos, "neg": n_neg}}
    if min(len(syn_pos), len(syn_neg), len(real_train_pos), len(real_train_neg), n_pos, n_neg) < 5:
        return {**base, "status": "insufficient input",
                "n": {"syn_pos": len(syn_pos), "syn_neg": len(syn_neg), "real_train_pos": len(real_train_pos),
                      "real_train_neg": len(real_train_neg), "test_pos": n_pos, "test_neg": n_neg}}
    a_mm = max(float(d_eq_mm), 2.0)
    shape = test_pos.shape[1:]
    chans = observer.lg_channels_3d(shape, a_mm)
    n_train = int(min(N_TRAIN, len(syn_pos), len(real_train_pos)))
    res: dict = {}
    sc = {}
    for arm, (tp, tn) in {"S": (syn_pos, syn_neg), "R": (real_train_pos, real_train_neg)}.items():
        sc[arm] = _readers(tp, tn, test_pos, test_neg, chans, n_readers, n_train, seed_hex, arm)
    a_s = mrmc.mrmc_auc(*sc["S"])
    a_r = mrmc.mrmc_auc(*sc["R"])
    d = mrmc.mrmc_delta_auc(sc["S"][0], sc["S"][1], sc["R"][0], sc["R"][1])
    res.update(base)
    res.update({"n_train": n_train, "auc_train_syn": a_s, "auc_train_real": a_r,
                "delta_auc": {"value": d["delta_auc"], "se": d["se"], "ci95": d["ci95"], "df": d["df"]},
                "channel_a_mm": a_mm,
                "powered": bool(n_pos >= VICTRE_HETERO["pos"] and n_neg >= VICTRE_HETERO["neg"]
                                and n_readers >= 30),
                "powered_note": f"VICTRE heterogeneous design is {VICTRE_HETERO['pos']} pos / {VICTRE_HETERO['neg']} neg"})
    types = np.array(test_pos_types)
    per_type = {}
    if all((types == t).sum() >= 10 for t in set(types)):
        for t in sorted(set(types)):
            m = types == t
            per_type[t] = {"n_pos": int(m.sum()),
                           "delta_auc": mrmc.mrmc_delta_auc(sc["S"][0], sc["S"][1][:, m], sc["R"][0], sc["R"][1][:, m])["delta_auc"]}
    res["per_type"] = per_type if per_type else {"status": "insufficient input (< 10 test positives in a type)"}
    # 2-D central-slice CHO for comparability with VICTRE (plan Q5)
    c2 = observer.lg_channels_2d(shape[1], a_mm)
    mid = shape[0] // 2
    sc2 = {arm: _readers(tp[:, mid], tn[:, mid], test_pos[:, mid], test_neg[:, mid], c2, min(n_readers, 10),
                         n_train, seed_hex, "2d" + arm)
           for arm, (tp, tn) in {"S": (syn_pos, syn_neg), "R": (real_train_pos, real_train_neg)}.items()}
    res["auc_2d_central_slice"] = {a: mrmc.mrmc_auc(*sc2[a])["auc"] for a in "SR"}
    res["_roc_scores"] = {a: [sc[a][1].mean(0).tolist(), sc[a][0].mean(0).tolist()] for a in "SR"}
    return res
