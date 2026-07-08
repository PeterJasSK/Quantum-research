#!/usr/bin/env python3
"""
qrng_compare.py  —  compare TWO QRNG bitstreams and emit ONE professional PDF report.

Takes two "bits:..." processed files and analyses FOUR streams side by side:
each file's RAW stream and its SHA-512 entropy-EXTRACTED ("whitened", 75% kept)
stream. Every chart shows all four streams together, and every chart is paired
with an equal, easy-to-read data table.

Tests:
  * Bias analysis in 20 even splits                    (chart + table)
  * NIST SP 800-22 battery in 5 partitions             (real `nistrng` ONLY)
  * Next-bit ML predictability — STRICT, multi-window  (embedded; from mashineLearning.py)
  * Markov dependency — multi-order                     (embedded; from mashineLearning.py)

(The Dieharder battery was removed: ~10M bits is far too little for it to be meaningful.)

This file is SELF-CONTAINED: the next-bit and Markov routines are embedded below.

USAGE
    python qrng_compare.py FILE1 FILE2 [-o report.pdf] [-n MAX_BITS]

    -o / --out    output PDF path            (default: qrng_report.pdf)
    -n / --bits   max bits to use per file   (default: 0 = use ALL; set small to
                                              test the report quickly, e.g. -n 100000)

REQUIREMENTS (hard — the script exits if missing)
    pip install nistrng scikit-learn matplotlib numpy
"""

import argparse
import base64
import hashlib
import io
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# scikit-learn is needed by the embedded next-bit test; flag it for require_tools()
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                                 roc_auc_score, log_loss)
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_OK = True
except Exception as _sk_err:
    _SKLEARN_OK = False
    _SKLEARN_ERR = str(_sk_err)

# NIST SP800-22 battery — pure-Python/numpy implementation, no nistrng needed.
# nist_pure.py must sit next to this file (or be importable via PYTHONPATH).
from nist_pure import nist_battery  # noqa: E402

# ===========================================================================
# CONFIG
# ===========================================================================
DEFAULT_MAX_BITS = 0            # 0 = use all bits in each file (override with -n)

BIAS_SPLITS = 20
NIST_SPLITS = 5
NIST_MAX_BITS_PER_PART = 1_000_000     # >= NIST's 1e6 minimum; caps runtime

EXTRACT_RATIO = 0.75                    # SHA-512 whitening keeps exactly 75%

# Stricter next-bit test: several windows, more folds, CI + tight alpha.
ML_WINDOWS = [8, 16, 24]               # a fail in ANY window fails the stream
ML_SPLITS = 8                          # time-ordered CV folds (more = stricter)
MAX_ML_BITS = 300_000                  # subsample cap for the ML test
ML_ALPHA = 0.01                        # predictable if p < ML_ALPHA

MARKOV_ORDERS = [1, 2, 4]              # first-, second-, fourth-order dependency
MAX_MARKOV_BITS = 1_000_000

# Practical-significance margins: with millions of bits, CIs get so tight that a
# negligible fluctuation is "significant". Flag structure only if the effect is
# both statistically significant AND at least this large (tune to taste).
NEXTBIT_AUC_MARGIN = 0.02              # AUC must exceed 0.5 by this to count as structure
NEXTBIT_ACC_MARGIN = 0.02             # accuracy must beat the bias baseline by this
MARKOV_MARGIN = 0.01                   # markov accuracy must beat baseline by this

NIST_ALPHA = 0.01                      # per-test pass threshold reference
NIST_PASS_RATE_OK = 0.90              # stream-level "pass" heuristic for verdicts
# ===========================================================================

# ===========================================================================
# EMBEDDED FROM YOUR mashineLearning.py  (next-bit ML test + Markov test)
# Kept functionally identical so results match your past work.
# ===========================================================================
def _to_bit_array(bitstream):
    if isinstance(bitstream, str):
        arr = np.array([int(b) for b in bitstream], dtype=np.int8)
    else:
        arr = np.array(bitstream, dtype=np.int8)
    if not np.all((arr == 0) | (arr == 1)):
        raise ValueError("bitstream must contain only 0/1 values")
    return arr


def _build_dataset(bitstream, window_size):
    X, y = [], []
    for i in range(len(bitstream) - window_size):
        X.append(bitstream[i:i + window_size])
        y.append(bitstream[i + window_size])
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int8)
    return X, y


def _time_series_folds(n_samples, n_splits=5, min_train_ratio=0.5):
    if n_samples < n_splits + 20:
        raise ValueError("Not enough samples for requested number of splits")
    min_train = max(20, int(n_samples * min_train_ratio))
    remaining = n_samples - min_train
    test_size = remaining // n_splits
    if test_size < 5:
        raise ValueError("Not enough data left for test folds after training prefix")
    folds = []
    for i in range(n_splits):
        train_end = min_train + i * test_size
        test_end = min(min_train + (i + 1) * test_size, n_samples)
        if test_end - train_end < 5:
            continue
        folds.append((np.arange(0, train_end), np.arange(train_end, test_end)))
    if not folds:
        raise ValueError("Could not create valid folds")
    return folds


def _majority_baseline(y_train, y_test):
    p1 = np.mean(y_train)
    pred_class = 1 if p1 >= 0.5 else 0
    return accuracy_score(y_test, np.full_like(y_test, pred_class))


def _normal_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def _binomial_test_greater(k, n, p=0.5):
    if n <= 0:
        return 1.0
    if not (0 <= k <= n):
        raise ValueError("k must satisfy 0 <= k <= n")
    if n <= 200:
        prob = 0.0
        for i in range(k, n + 1):
            prob += math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
        return min(1.0, max(0.0, prob))
    mu = n * p
    sigma = math.sqrt(n * p * (1 - p))
    if sigma == 0:
        return 1.0 if k <= mu else 0.0
    z = (k - 0.5 - mu) / sigma
    return min(1.0, max(0.0, _normal_sf(z)))


def next_bit_test_crossval(bitstream, window_size=8, n_splits=5,
                           model_type="logreg", min_train_ratio=0.5):
    bits = _to_bit_array(bitstream)
    if len(bits) <= window_size + 30:
        raise ValueError("Bitstream too short for reliable next-bit testing")
    X, y = _build_dataset(bits, window_size)
    folds = _time_series_folds(len(X), n_splits=n_splits, min_train_ratio=min_train_ratio)

    if model_type == "logreg":
        model = Pipeline([("scaler", StandardScaler()),
                          ("clf", LogisticRegression(random_state=42, max_iter=2000,
                                                     solver="lbfgs"))])
    else:
        raise ValueError("Currently supported model_type: 'logreg'")

    fold_results, all_y_true, all_y_pred, all_y_prob = [], [], [], []
    for fold_id, (train_idx, test_idx) in enumerate(folds, start=1):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        if len(np.unique(y_train)) < 2:
            only_class = int(y_train[0])
            y_prob = np.full(len(y_test), float(only_class))
            y_pred = np.full(len(y_test), only_class, dtype=np.int8)
        else:
            model.fit(X_train, y_train)
            y_prob = model.predict_proba(X_test)[:, 1]
            y_pred = (y_prob >= 0.5).astype(np.int8)

        acc = accuracy_score(y_test, y_pred)
        bal_acc = balanced_accuracy_score(y_test, y_pred)
        try:
            auc = roc_auc_score(y_test, y_prob)
        except ValueError:
            auc = float("nan")
        try:
            ll = log_loss(y_test, np.clip(y_prob, 1e-8, 1 - 1e-8))
        except ValueError:
            ll = float("nan")
        baseline_acc = _majority_baseline(y_train, y_test)
        correct = int(np.sum(y_pred == y_test)); total = int(len(y_test))
        p_value = _binomial_test_greater(correct, total, p=0.5)
        fold_results.append({
            "fold": fold_id, "train_size": int(len(train_idx)), "test_size": total,
            "accuracy": float(acc), "balanced_accuracy": float(bal_acc),
            "auc": None if np.isnan(auc) else float(auc),
            "log_loss": None if np.isnan(ll) else float(ll),
            "majority_baseline_accuracy": float(baseline_acc),
            "correct_predictions": correct,
            "binomial_p_value_vs_0_5": float(p_value)})
        all_y_true.extend(y_test.tolist()); all_y_pred.extend(y_pred.tolist())
        all_y_prob.extend(y_prob.tolist())

    all_y_true = np.array(all_y_true, dtype=np.int8)
    all_y_pred = np.array(all_y_pred, dtype=np.int8)
    all_y_prob = np.array(all_y_prob, dtype=np.float64)
    overall_acc = accuracy_score(all_y_true, all_y_pred)
    overall_bal_acc = balanced_accuracy_score(all_y_true, all_y_pred)
    try:
        overall_auc = roc_auc_score(all_y_true, all_y_prob)
    except ValueError:
        overall_auc = float("nan")
    try:
        overall_ll = log_loss(all_y_true, np.clip(all_y_prob, 1e-8, 1 - 1e-8))
    except ValueError:
        overall_ll = float("nan")
    overall_correct = int(np.sum(all_y_true == all_y_pred))
    overall_total = int(len(all_y_true))
    overall_p = _binomial_test_greater(overall_correct, overall_total, p=0.5)

    if overall_p < 0.01 and overall_acc > 0.5:
        interpretation = ("Model predicts next bit significantly better than chance. "
                          "This suggests detectable structure / pseudo-randomness.")
    elif overall_p >= 0.01 and 0.48 <= overall_acc <= 0.52:
        interpretation = ("Model is near chance level and not statistically better than "
                          "random. This bitstream does not show easily learnable next-bit "
                          "structure.")
    else:
        interpretation = ("Result is inconclusive. There may be weak structure, but "
                          "evidence is not strong.")

    fold_labels = [r["fold"] for r in fold_results]
    accs = [r["accuracy"] for r in fold_results]
    baselines = [r["majority_baseline_accuracy"] for r in fold_results]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(fold_labels)); width = 0.38
    ax.bar(x - width / 2, accs, width, label="Model accuracy")
    ax.bar(x + width / 2, baselines, width, label="Majority baseline")
    ax.axhline(0.5, color="red", linestyle="--", linewidth=1.5, label="Chance = 0.5")
    ax.set_xticks(x); ax.set_xticklabels([f"Fold {f}" for f in fold_labels])
    ax.set_ylim(0, 1); ax.set_xlabel("Time-ordered fold"); ax.set_ylabel("Accuracy")
    ax.set_title(f"Next-Bit Predictability Test (window_size={window_size})")
    ax.legend()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight"); plt.close(fig)
    buffer.seek(0)
    chart_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {"summary": {"window_size": window_size, "n_splits": len(fold_results),
                        "total_samples": int(len(X)),
                        "overall_accuracy": float(overall_acc),
                        "overall_balanced_accuracy": float(overall_bal_acc),
                        "overall_auc": None if np.isnan(overall_auc) else float(overall_auc),
                        "overall_log_loss": None if np.isnan(overall_ll) else float(overall_ll),
                        "overall_correct_predictions": overall_correct,
                        "overall_test_predictions": overall_total,
                        "overall_binomial_p_value_vs_0_5": float(overall_p),
                        "interpretation": interpretation},
            "folds": fold_results, "chart": chart_base64}


def next_bit_markov_test(bitstream, window_size=8, train_ratio=0.7):
    bits = _to_bit_array(bitstream)
    X, y = _build_dataset(bits, window_size)
    split = int(len(X) * train_ratio)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    counts = defaultdict(Counter)
    global_p1 = float(np.mean(y_train))
    for x, target in zip(X_train, y_train):
        counts[tuple(x)][int(target)] += 1
    preds = []
    for x in X_test:
        key = tuple(x)
        if key in counts:
            total = counts[key][0] + counts[key][1]
            p1 = counts[key][1] / total
        else:
            p1 = global_p1
        preds.append(1 if p1 >= 0.5 else 0)
    preds = np.array(preds)
    acc = accuracy_score(y_test, preds)
    bal_acc = balanced_accuracy_score(y_test, preds)
    p_value = _binomial_test_greater(int(np.sum(preds == y_test)), len(y_test), p=0.5)
    return {"accuracy": float(acc), "balanced_accuracy": float(bal_acc),
            "p_value_vs_0_5": float(p_value), "test_size": int(len(y_test))}
# ===========================================================================
# END embedded block
# ===========================================================================



# ---------------------------------------------------------------------------
# requirements (checked in main so functions stay importable/testable)
# ---------------------------------------------------------------------------
def require_tools():
    missing = []
    if not _SKLEARN_OK:
        missing.append(f"scikit-learn  (pip install scikit-learn)  [{_SKLEARN_ERR}]")
    if missing:
        print("ERROR — required components missing:")
        for m in missing:
            print("  -", m)
        sys.exit(1)


# ---------------------------------------------------------------------------
# IO / basic stats
# ---------------------------------------------------------------------------
def load_bits(path, max_bits=0):
    with open(path) as f:
        s = f.read().strip()
    if s.startswith("bits:"):
        s = s[5:]
    s = s.strip()
    arr = np.frombuffer(s.encode("ascii"), dtype=np.uint8).astype(np.int8) - ord("0")
    if arr.size and arr.max() > 1:
        raise ValueError(f"{path}: contains non 0/1 characters")
    if max_bits and max_bits > 0:
        arr = arr[:max_bits]
    return arr


def bits_to_str(arr):
    return (arr.astype(np.uint8) + ord("0")).tobytes().decode("ascii")


def label_for(path):
    m = re.match(r"^(noise|bell)_(.+)_(\d{8}-\d{6})_processed\.txt$",
                 os.path.basename(path))
    if m:
        return f"{m.group(1)} / {m.group(2)}"
    return os.path.splitext(os.path.basename(path))[0]


def global_bias(arr):
    return abs(float(arr.mean()) - 0.5) if arr.size else 0.0


def min_entropy_rate(bias):
    p = 0.5 + bias
    return -math.log2(p) if 0 < p <= 1 else 0.0


def wilson_ci(k, n, z=1.96):
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def auc_ci_hanley(auc, n_pos, n_neg, z=1.96):
    """95% CI for AUC via the Hanley–McNeil variance (bias-robust structure signal)."""
    if auc is None or n_pos < 1 or n_neg < 1:
        return (None, None)
    q1 = auc / (2 - auc)
    q2 = 2 * auc * auc / (1 + auc)
    var = (auc * (1 - auc) + (n_pos - 1) * (q1 - auc * auc)
           + (n_neg - 1) * (q2 - auc * auc)) / (n_pos * n_neg)
    se = math.sqrt(max(var, 0.0))
    return (max(0.0, auc - z * se), min(1.0, auc + z * se))


# ---------------------------------------------------------------------------
# bias in N splits
# ---------------------------------------------------------------------------
def bias_splits(arr, n):
    L = len(arr); size = L // n if n else L
    out = []
    for i in range(n):
        a = i * size
        b = (i + 1) * size if i < n - 1 else L
        c = arr[a:b]; tot = len(c); ones = int(c.sum())
        out.append({"split": i + 1, "bias": abs(ones / tot - 0.5) if tot else 0.0,
                    "p1": ones / tot if tot else 0.0})
    return out


# ---------------------------------------------------------------------------
# NIST battery — now provided by nist_pure.nist_battery() (imported above).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SHA-512 whitening extractor (keeps exactly EXTRACT_RATIO)
# ---------------------------------------------------------------------------
def hash_extract(arr, ratio=EXTRACT_RATIO):
    arr = arr[: len(arr) // 8 * 8]
    data = np.packbits(arr.astype(np.uint8)).tobytes()
    IN = 64
    OUT = max(1, min(64, int(round(IN * ratio))))
    out = bytearray()
    i = 0
    while i + IN <= len(data):
        out += hashlib.sha512(data[i:i + IN]).digest()[:OUT]
        i += IN
    tail = data[i:]
    if tail:
        out += hashlib.sha512(tail).digest()[:min(64, math.ceil(len(tail) * ratio))]
    if not out:
        return arr.copy()
    return np.unpackbits(np.frombuffer(bytes(out), dtype=np.uint8)).astype(np.int8)


# ---------------------------------------------------------------------------
# STRICT next-bit predictability (multi-window, more folds, Wilson CI)
# ---------------------------------------------------------------------------
def strict_next_bit(arr):
    """Bias-robust structure detection: AUC (with CI) is the primary signal, since
    AUC ~ 0.5 even for a biased-but-independent stream; structure -> AUC > 0.5.
    Also checks whether accuracy beats the majority (bias-only) baseline."""
    sample = arr[:MAX_ML_BITS]
    s = bits_to_str(sample)
    p1 = float(sample.mean()) if len(sample) else 0.5
    baseline = max(p1, 1 - p1)                 # majority (bias-only) accuracy
    per = {}
    verdict = "PASS"
    worst_auc, min_p = 0.5, 1.0
    for w in ML_WINDOWS:
        try:
            r = next_bit_test_crossval(s, window_size=w, n_splits=ML_SPLITS)["summary"]
            acc = r["overall_accuracy"]
            n = r["overall_test_predictions"]
            correct = r["overall_correct_predictions"]
            p = r["overall_binomial_p_value_vs_0_5"]
            auc = r["overall_auc"]
            n_pos = max(0, min(n, round(p1 * n))); n_neg = n - n_pos
            alo, ahi = auc_ci_hanley(auc, n_pos, n_neg)
            acc_lo, acc_hi = wilson_ci(correct, n)
            # STRUCTURE (fail) if AUC is significantly AND materially above 0.5, OR
            # accuracy materially beats the bias-only baseline. Pure bias / negligible
            # fluctuations do NOT trigger this (practical-significance margins).
            structure = ((alo is not None and alo > 0.5 + NEXTBIT_AUC_MARGIN)
                         or (acc_lo > baseline + NEXTBIT_ACC_MARGIN))
            per[w] = {"accuracy": acc, "baseline": baseline, "auc": auc,
                      "auc_ci": (alo, ahi), "acc_ci": (acc_lo, acc_hi),
                      "p_value": p, "n_test": n, "pass": not structure}
            worst_auc = max(worst_auc, auc if auc is not None else 0.5)
            min_p = min(min_p, p)
            if structure:
                verdict = "FAIL"
        except Exception as e:
            per[w] = {"error": str(e)}
            if verdict == "PASS":
                verdict = "INCONCLUSIVE"
    return {"per_window": per, "verdict": verdict, "worst_auc": worst_auc,
            "baseline": baseline, "min_p": min_p, "windows": ML_WINDOWS,
            "folds": ML_SPLITS, "samples": len(s)}


def markov_multi(arr):
    """Bias-robust: dependency = accuracy significantly beats the majority baseline."""
    sample = arr[:MAX_MARKOV_BITS]
    s = bits_to_str(sample)
    p1 = float(sample.mean()) if len(sample) else 0.5
    baseline = max(p1, 1 - p1)
    per = {}
    verdict = "PASS"
    max_excess = 0.0
    for order in MARKOV_ORDERS:
        try:
            r = next_bit_markov_test(s, window_size=order)
            acc = r["accuracy"]; n = r["test_size"]; correct = round(acc * n)
            lo, hi = wilson_ci(correct, n)
            dependency = lo > baseline + MARKOV_MARGIN
            per[order] = {"accuracy": acc, "baseline": baseline, "acc_ci": (lo, hi),
                          "p_value": r["p_value_vs_0_5"], "dependency": dependency}
            max_excess = max(max_excess, acc - baseline)
            if dependency:
                verdict = "FAIL"
        except Exception as e:
            per[order] = {"error": str(e)}
            if verdict == "PASS":
                verdict = "INCONCLUSIVE"
    return {"per_order": per, "verdict": verdict, "baseline": baseline,
            "max_excess": max_excess, "orders": MARKOV_ORDERS}


def analyze(arr):
    b = global_bias(arr)
    return {"n_bits": int(len(arr)), "global_bias": b,
            "min_entropy_per_bit": min_entropy_rate(b),
            "bias_splits": bias_splits(arr, BIAS_SPLITS),
            "nist": nist_battery(arr),
            "next_bit": strict_next_bit(arr),
            "markov": markov_multi(arr)}


# ===========================================================================
# PDF reporting
# ===========================================================================
PAGE = (8.27, 11.69)   # A4 portrait


def _title_block(fig, title, subtitle=""):
    fig.text(0.06, 0.95, title, fontsize=15, weight="bold")
    if subtitle:
        fig.text(0.06, 0.925, subtitle, fontsize=9.5, color="#555555")


def _caption(fig, text, y=0.055):
    fig.text(0.06, y, text, ha="left", va="bottom", fontsize=8.3,
             wrap=True, color="#333333")


def _style_header(tbl, ncols):
    for c in range(ncols):
        tbl[0, c].set_facecolor("#2c3e50")
        tbl[0, c].set_text_props(color="white", weight="bold")


def table_page(pdf, title, col_labels, rows, caption="", max_rows=24, fontsize=8):
    rows = rows if rows else [["(no data)"] + [""] * (len(col_labels) - 1)]
    for start in range(0, len(rows), max_rows):
        chunk = rows[start:start + max_rows]
        fig = plt.figure(figsize=PAGE)
        suffix = "" if len(rows) <= max_rows else f"   (rows {start+1}–{start+len(chunk)} of {len(rows)})"
        _title_block(fig, title + suffix, "Data table (same numbers as the chart)")
        ax = fig.add_axes([0.05, 0.12, 0.90, 0.74]); ax.axis("off")
        tbl = ax.table(cellText=chunk, colLabels=col_labels, cellLoc="center",
                       loc="upper center")
        tbl.auto_set_font_size(False); tbl.set_fontsize(fontsize); tbl.scale(1, 1.45)
        _style_header(tbl, len(col_labels))
        if caption:
            _caption(fig, caption)
        pdf.savefig(fig); plt.close(fig)


# ---- stream registry: 2 files x {raw, whitened} = 4 streams -----------------
def build_streams(res1, res2, l1, l2):
    return [
        {"name": f"{l1} (raw)",       "short": _short(l1, "raw"),   "res": res1["raw"], "color": "#1f77b4", "ls": "-",  "hatch": ""},
        {"name": f"{l1} (whitened)",  "short": _short(l1, "white"), "res": res1["ext"], "color": "#7fb9e6", "ls": "--", "hatch": "//"},
        {"name": f"{l2} (raw)",       "short": _short(l2, "raw"),   "res": res2["raw"], "color": "#d62728", "ls": "-",  "hatch": ""},
        {"name": f"{l2} (whitened)",  "short": _short(l2, "white"), "res": res2["ext"], "color": "#f2a5a5", "ls": "--", "hatch": "//"},
    ]


def _short(label, variant):
    s = label.replace(" / ", "/").replace("ibm_", "")
    return f"{s}\n{variant}"


# ---- Page: run overview + summary table ------------------------------------
def page_summary(pdf, streams, meta):
    fig = plt.figure(figsize=PAGE)
    _title_block(fig, "QRNG comparison report",
                 f"{meta['file1']}  vs  {meta['file2']}\nGenerated {meta['ts']}")
    fig.text(0.06, 0.885,
             f"Bits used per file: {meta['bits_used']}   |   NIST bits/partition: "
             f"{streams[0]['res']['nist']['bits_per_partition']:,}   |   "
             f"ML windows {ML_WINDOWS}, {ML_SPLITS} folds   |   Markov orders {MARKOV_ORDERS}",
             fontsize=8.5, color="#555")

    metrics = [
        ("Total bits",            lambda r: f"{r['n_bits']:,}"),
        ("Global bias |p1-0.5|",  lambda r: f"{r['global_bias']:.4f}"),
        ("Min-entropy / bit",     lambda r: f"{r['min_entropy_per_bit']:.4f}"),
        ("NIST pass rate",        lambda r: f"{r['nist']['overall_pass_rate']:.2f}"),
        ("NIST passed / run",     lambda r: f"{r['nist']['tests_passed']}/{r['nist']['tests_run']}"),
        ("Next-bit verdict",      lambda r: r['next_bit']['verdict']),
        ("Next-bit worst AUC",    lambda r: f"{r['next_bit']['worst_auc']:.4f}"),
        ("Markov verdict",        lambda r: r['markov']['verdict']),
        ("Markov max excess",     lambda r: f"{r['markov']['max_excess']:.4f}"),
    ]
    col_labels = ["Metric"] + [s["short"].replace("\n", " ") for s in streams]
    rows = [[name] + [fn(s["res"]) for s in streams] for name, fn in metrics]
    ax = fig.add_axes([0.04, 0.30, 0.92, 0.52]); ax.axis("off")
    tbl = ax.table(cellText=rows, colLabels=col_labels, cellLoc="center", loc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(8); tbl.scale(1, 1.6)
    _style_header(tbl, len(col_labels))
    _caption(fig,
             "All four streams side by side: each input file contributes its RAW stream and its "
             "WHITENED (SHA-512, 75% kept) stream. Lower bias is better; min-entropy near 1.0 is "
             "better;\nNIST pass rate near 1.0 is better; next-bit / Markov verdict PASS means no "
             "detectable structure (accuracy ~0.5 with p >= 0.01 and a 95% CI that includes 0.5).",
             y=0.16)
    pdf.savefig(fig); plt.close(fig)


# ---- Page: bias per 20 splits (chart) + table ------------------------------
def page_bias(pdf, streams):
    fig = plt.figure(figsize=PAGE)
    _title_block(fig, "Bias per segment (20 splits)",
                 "Local balance along each stream — all four streams overlaid")
    ax = fig.add_axes([0.10, 0.34, 0.84, 0.50])
    xs = [d["split"] for d in streams[0]["res"]["bias_splits"]]
    for s in streams:
        ys = [d["bias"] for d in s["res"]["bias_splits"]]
        ax.plot(xs, ys, marker="o", markersize=3, color=s["color"], linestyle=s["ls"],
                label=f"{s['name']} (global {s['res']['global_bias']:.4f})")
    ax.set_xlabel("Segment (each ≈ 1/20 of the stream)")
    ax.set_ylabel("Bias  |p1 − 0.5|")
    ax.set_xticks(xs); ax.grid(alpha=0.3); ax.legend(fontsize=7.5, loc="upper right")
    _caption(fig,
             "Each stream is cut into 20 equal segments; the plotted value is how far that segment's "
             "fraction of ones sits from 0.5. Solid lines = raw, dashed = whitened. A good source is "
             "LOW and FLAT:\nno segment drifts and there is no rising/falling trend. Whitened lines "
             "should sit near the bottom regardless of how their raw counterpart behaves — that is "
             "the extractor removing residual imbalance. Reading tip: compare the two SOLID (raw) "
             "lines to judge the hardware; the dashed lines show what post-processing recovers.")
    pdf.savefig(fig); plt.close(fig)

    # table: 20 rows x 4 streams
    col = ["Split"] + [s["short"].replace("\n", " ") for s in streams]
    rows = []
    for i, d0 in enumerate(streams[0]["res"]["bias_splits"]):
        row = [str(d0["split"])]
        for s in streams:
            row.append(f"{s['res']['bias_splits'][i]['bias']:.4f}")
        rows.append(row)
    table_page(pdf, "Bias per segment — data (|p1 − 0.5| per split)", col, rows,
               caption="Same values as the chart above. Lower is better; look for any column that is "
                       "systematically larger (a more biased stream) or any single spiking row "
                       "(localised imbalance).")


# ---- Page: global bias raw vs whitened (chart) + table ---------------------
def page_global_bias(pdf, streams):
    fig = plt.figure(figsize=PAGE)
    _title_block(fig, "Global bias & min-entropy — raw vs whitened",
                 "Whole-stream imbalance for all four streams")
    ax = fig.add_axes([0.10, 0.40, 0.84, 0.44])
    x = np.arange(len(streams))
    vals = [s["res"]["global_bias"] for s in streams]
    ax.bar(x, vals, color=[s["color"] for s in streams])
    ax.set_xticks(x); ax.set_xticklabels([s["short"] for s in streams], fontsize=8)
    ax.set_ylabel("Global bias  |p1 − 0.5|"); ax.grid(alpha=0.3, axis="y")
    for xi, v in zip(x, vals):
        ax.text(xi, v, f"{v:.4f}", ha="center", va="bottom", fontsize=8)
    _caption(fig,
             "Whole-stream bias (one number per stream). The whitened bars should be far lower than "
             "their raw counterparts — direct evidence the SHA-512 extractor removes imbalance while "
             "keeping\n75% of the data. Min-entropy per bit (table) converts bias to 'how many bits "
             "of true randomness per output bit'; 1.0 is ideal.")
    pdf.savefig(fig); plt.close(fig)

    col = ["Metric"] + [s["short"].replace("\n", " ") for s in streams]
    rows = [
        ["Global bias"]      + [f"{s['res']['global_bias']:.4f}" for s in streams],
        ["Min-entropy/bit"]  + [f"{s['res']['min_entropy_per_bit']:.4f}" for s in streams],
        ["Total bits"]       + [f"{s['res']['n_bits']:,}" for s in streams],
    ]
    table_page(pdf, "Global bias & min-entropy — data", col, rows,
               caption="Same numbers as the chart. Compare each raw stream with its whitened version "
                       "to quantify how much structure the extractor removed.")


# ---- Page: NIST battery (chart) + table ------------------------------------
def page_nist(pdf, streams):
    names = sorted(set().union(*[set(s["res"]["nist"]["per_test"]) for s in streams]))
    fig = plt.figure(figsize=PAGE)
    _title_block(fig, "NIST SP 800-22 — partitions passed per test",
                 "Out of 5 partitions; all four streams grouped per test")
    ax = fig.add_axes([0.34, 0.14, 0.60, 0.72])
    y = np.arange(len(names)); h = 0.8 / len(streams)
    for k, s in enumerate(streams):
        vals = [s["res"]["nist"]["per_test"].get(n, {}).get("pass", 0) for n in names]
        ax.barh(y + (k - (len(streams) - 1) / 2) * h, vals, h,
                color=s["color"], label=s["name"])
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=6.5)
    ax.set_xlabel("Partitions passed (of 5)"); ax.set_xlim(0, NIST_SPLITS)
    ax.invert_yaxis(); ax.legend(fontsize=6.5, loc="lower right"); ax.grid(alpha=0.3, axis="x")
    rates = "   ".join(f"{s['short'].replace(chr(10),' ')}: {s['res']['nist']['overall_pass_rate']:.2f}"
                       for s in streams)
    fig.text(0.06, 0.90, "Overall pass rate — " + rates, fontsize=7.5)
    _caption(fig,
             "The full NIST SP 800-22 battery runs on 5 partitions of each stream; a bar of 5 means "
             "the test passed in every partition (p > 0.01 each). Longer is better. Tests that need "
             "more bits\nthan a partition provides are skipped by the library (so the test list can "
             "differ between streams if bit counts differ). Whitened streams should reach 5 across "
             "the board.", y=0.05)
    pdf.savefig(fig); plt.close(fig)

    col = ["NIST test"] + [s["short"].replace("\n", " ") for s in streams]
    rows = []
    for n in names:
        row = [n]
        for s in streams:
            d = s["res"]["nist"]["per_test"].get(n)
            row.append(f"{d['pass']}/{d['run']}" if d else "—")
        rows.append(row)
    rows.append(["OVERALL pass rate"] +
                [f"{s['res']['nist']['overall_pass_rate']:.2f}" for s in streams])
    table_page(pdf, "NIST SP 800-22 — data (partitions passed / run)", col, rows,
               caption="Same values as the chart. '4/5' means the test passed in 4 of the 5 "
                       "partitions. '—' means the test was not eligible for that stream's length.",
               fontsize=7)


# ---- Page: strict next-bit (chart) + table ---------------------------------
def page_nextbit(pdf, streams):
    fig = plt.figure(figsize=PAGE)
    _title_block(fig, "Next-bit predictability — strict, bias-robust (AUC)",
                 "AUC vs window size; 0.5 = no learnable structure")
    ax = fig.add_axes([0.10, 0.36, 0.84, 0.48])
    for s in streams:
        pw = s["res"]["next_bit"]["per_window"]
        ws = [w for w in ML_WINDOWS if "auc" in pw.get(w, {}) and pw[w]["auc"] is not None]
        aucs = [pw[w]["auc"] for w in ws]
        lo = [pw[w]["auc"] - (pw[w]["auc_ci"][0] or pw[w]["auc"]) for w in ws]
        hi = [(pw[w]["auc_ci"][1] or pw[w]["auc"]) - pw[w]["auc"] for w in ws]
        ax.errorbar(ws, aucs, yerr=[lo, hi], marker="o", capsize=3, color=s["color"],
                    linestyle=s["ls"], label=f"{s['name']} [{s['res']['next_bit']['verdict']}]")
    ax.axhline(0.5, color="green", linestyle=":", label="chance AUC = 0.5")
    ax.set_xlabel("Window size (previous bits used to predict the next)")
    ax.set_ylabel("ROC AUC (95% Hanley–McNeil CI)")
    ax.set_xticks(ML_WINDOWS); ax.grid(alpha=0.3); ax.legend(fontsize=7)
    _caption(fig,
             f"A logistic-regression model predicts each bit from the previous W bits, "
             f"{ML_SPLITS}-fold time-ordered CV, for W in {ML_WINDOWS}. We use ROC AUC as the primary "
             f"signal because it is BIAS-ROBUST: a biased-but-independent stream still gives AUC ~ 0.5, "
             f"whereas plain accuracy would rise just from guessing the majority bit. Structure is "
             f"flagged only if a window's AUC 95% CI lies ABOVE 0.5 (or accuracy beats the majority "
             f"baseline). Verdict in the legend is the strict AND over all windows. (Raw bias itself is "
             f"reported separately in the bias analysis.)")
    pdf.savefig(fig); plt.close(fig)

    col = ["Stream", "Window", "Accuracy", "Majority base", "AUC", "AUC 95% CI", "p", "pass"]
    rows = []
    for s in streams:
        pw = s["res"]["next_bit"]["per_window"]
        for w in ML_WINDOWS:
            d = pw.get(w, {})
            if "auc" in d:
                alo, ahi = d["auc_ci"]
                rows.append([s["short"].replace("\n", " "), str(w),
                             f"{d['accuracy']:.4f}", f"{d['baseline']:.4f}",
                             "n/a" if d["auc"] is None else f"{d['auc']:.4f}",
                             "n/a" if alo is None else f"[{alo:.3f},{ahi:.3f}]",
                             f"{d['p_value']:.3f}",
                             "PASS" if d["pass"] else "FAIL"])
            else:
                rows.append([s["short"].replace("\n", " "), str(w), "err", "", "", "", "",
                             d.get("error", "?")[:14]])
    table_page(pdf, "Next-bit predictability — data (per stream × window)", col, rows,
               caption="'Majority base' = accuracy obtainable by always guessing the more common bit "
                       "(pure bias). A window PASSES when AUC's CI includes/sits at 0.5 AND accuracy "
                       "does not significantly exceed the majority baseline.", fontsize=7.5)


# ---- Page: Markov (chart) + table ------------------------------------------
def page_markov(pdf, streams):
    fig = plt.figure(figsize=PAGE)
    _title_block(fig, "Markov dependency — multi-order (bias-robust)",
                 "Accuracy ABOVE the majority baseline; 0 = no dependency")
    ax = fig.add_axes([0.10, 0.40, 0.84, 0.44])
    x = np.arange(len(MARKOV_ORDERS)); w = 0.8 / len(streams)
    for k, s in enumerate(streams):
        po = s["res"]["markov"]["per_order"]
        vals = [max(0.0, po.get(o, {}).get("accuracy", 0.0) - po.get(o, {}).get("baseline", 0.0))
                if "accuracy" in po.get(o, {}) else 0.0 for o in MARKOV_ORDERS]
        ax.bar(x + (k - (len(streams) - 1) / 2) * w, vals, w, color=s["color"], label=s["name"])
    ax.axhline(0.0, color="green", linestyle=":")
    ax.set_xticks(x); ax.set_xticklabels([f"order {o}" for o in MARKOV_ORDERS])
    ax.set_ylabel("Accuracy − majority baseline")
    ax.legend(fontsize=7); ax.grid(alpha=0.3, axis="y")
    _caption(fig,
             "A k-th order Markov predictor guesses the next bit from the previous k bits. We plot how "
             "far its accuracy exceeds the MAJORITY (bias-only) baseline, so pure bias reads as ~0 — "
             "only genuine short-range DEPENDENCY lifts a bar above the green line. Whitened streams "
             "should sit at 0 at every order. (Overall bias is reported separately.)")
    pdf.savefig(fig); plt.close(fig)

    col = ["Stream"] + [f"o{o} acc" for o in MARKOV_ORDERS] + ["base"] + \
          [f"o{o} excess" for o in MARKOV_ORDERS] + ["verdict"]
    rows = []
    for s in streams:
        po = s["res"]["markov"]["per_order"]
        base = s["res"]["markov"]["baseline"]
        accs = [f"{po.get(o, {}).get('accuracy', float('nan')):.4f}" for o in MARKOV_ORDERS]
        exc = [f"{(po.get(o, {}).get('accuracy', base) - base):.4f}" for o in MARKOV_ORDERS]
        rows.append([s["short"].replace("\n", " ")] + accs + [f"{base:.4f}"] + exc
                    + [s["res"]["markov"]["verdict"]])
    table_page(pdf, "Markov dependency — data (accuracy, baseline, excess per order)", col, rows,
               caption="'base' = majority baseline (pure bias). 'excess' = accuracy − baseline; a "
                       "positive, statistically significant excess at any order flags dependency and "
                       "fails the Markov verdict.", fontsize=7.5)


# ---- Page: conclusions ------------------------------------------------------
def _stream_verdict(r):
    nist_ok = r["nist"]["overall_pass_rate"] >= NIST_PASS_RATE_OK
    nb_ok = r["next_bit"]["verdict"] == "PASS"
    mk_ok = r["markov"]["verdict"] == "PASS"
    return "PASS" if (nist_ok and nb_ok and mk_ok) else "FAIL", nist_ok, nb_ok, mk_ok


def page_conclusions(pdf, streams):
    fig = plt.figure(figsize=PAGE)
    _title_block(fig, "Conclusions", "Strict per-stream verdict and raw-hardware comparison")
    col = ["Stream", "Bias", "NIST", "Next-bit", "Markov", "OVERALL"]
    rows = []
    for s in streams:
        r = s["res"]; overall, no, nbo, mko = _stream_verdict(r)
        rows.append([s["short"].replace("\n", " "), f"{r['global_bias']:.4f}",
                     "OK" if no else "low", "PASS" if nbo else "FAIL",
                     "PASS" if mko else "FAIL", overall])
    ax = fig.add_axes([0.05, 0.50, 0.90, 0.32]); ax.axis("off")
    tbl = ax.table(cellText=rows, colLabels=col, cellLoc="center", loc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.7)
    _style_header(tbl, len(col))

    # raw-vs-raw hardware comparison (the two solid lines)
    raws = [s for s in streams if "(raw)" in s["name"]]
    lines = []
    if len(raws) == 2:
        a, b = raws
        lo = a if a["res"]["global_bias"] <= b["res"]["global_bias"] else b
        lines.append(f"Hardware (raw) comparison: lower global bias = "
                     f"{lo['name']} ({lo['res']['global_bias']:.4f} vs "
                     f"{(b if lo is a else a)['res']['global_bias']:.4f}).")
    lines.append("Strict next-bit = multi-window logistic-regression CV with Wilson CIs; a single "
                 "predictable window fails the stream. Markov spans orders "
                 f"{MARKOV_ORDERS}.")
    lines.append("Note: whitened streams typically PASS everything — a good extractor whitens any "
                 "high-entropy source — so judge the HARDWARE on the RAW rows, and read the whitened "
                 "rows as 'what post-processing delivers'.")
    fig.text(0.06, 0.40, "\n\n".join(_wrap(l) for l in lines), fontsize=9, va="top")
    _caption(fig,
             "OVERALL PASS requires: NIST pass rate >= "
             f"{NIST_PASS_RATE_OK:.2f}, next-bit verdict PASS, and Markov verdict PASS. This is a "
             "guide, not a formal certification; sample size and calibration still matter.")
    pdf.savefig(fig); plt.close(fig)


def _wrap(text, width=110):
    import textwrap
    return "\n".join(textwrap.wrap(text, width))


def build_pdf(path, streams, meta):
    with PdfPages(path) as pdf:
        page_summary(pdf, streams, meta)
        page_bias(pdf, streams)
        page_global_bias(pdf, streams)
        page_nist(pdf, streams)
        page_nextbit(pdf, streams)
        page_markov(pdf, streams)
        page_conclusions(pdf, streams)
        d = pdf.infodict()
        d["Title"] = f"QRNG comparison: {meta['file1']} vs {meta['file2']}"
        d["Author"] = "qrng_compare.py"
        d["CreationDate"] = datetime.now()


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="Compare two QRNG bitstreams -> one PDF report.")
    ap.add_argument("file1")
    ap.add_argument("file2")
    ap.add_argument("-o", "--out", default="qrng_report.pdf", help="output PDF path")
    ap.add_argument("-n", "--bits", type=int, default=DEFAULT_MAX_BITS,
                    help="max bits per file (0 = use all; set small to test quickly)")
    args = ap.parse_args()

    require_tools()
    l1, l2 = label_for(args.file1), label_for(args.file2)
    cap = "ALL" if not args.bits else f"{args.bits:,}"
    print(f"Sample 1: {l1}  ({args.file1})")
    print(f"Sample 2: {l2}  ({args.file2})")
    print(f"Max bits per file: {cap}")

    results = {}
    for tag, path in (("1", args.file1), ("2", args.file2)):
        arr = load_bits(path, args.bits)
        print(f"\n[{tag}] {len(arr):,} bits loaded, bias {global_bias(arr):.4f} — running battery (raw)...")
        raw = analyze(arr)
        print(f"[{tag}] whitening (75%) and re-running battery...")
        ext = analyze(hash_extract(arr))
        results[tag] = {"raw": raw, "ext": ext}

    streams = build_streams(results["1"], results["2"], l1, l2)
    meta = {"file1": os.path.basename(args.file1), "file2": os.path.basename(args.file2),
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"), "bits_used": cap}
    print(f"\nWriting PDF -> {args.out}")
    build_pdf(args.out, streams, meta)
    print("Done.")


if __name__ == "__main__":
    main()