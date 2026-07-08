# rng/utils.py
import base64
import hashlib
import io
import json
from itertools import count
from pathlib import Path
import math
from collections import Counter
import numpy as np
from matplotlib import pyplot as plt
from ..models import QuantumShotResult
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


def load_local_results(json_path="results.json"):
    path = Path(json_path)
    with open(path, "r") as f:
        data = json.load(f)

    measurements = data["measurements"]
    batch_id = data["taskMetadata"]["id"]

    # measured qubits in order (length 50, skips 33,37,42,44)
    measured_qubits = data["measuredQubits"]

    pairs = [
        (1, 2), (3, 4), (8, 9), (15, 16), (23, 24),
        (10, 18), (17, 25), (5, 11), (6, 7), (20, 12),
        (13, 14), (19, 27), (21, 29), (22, 30), (32, 40),
        (26, 34), (28, 36), (31, 39), (35, 43), (38, 46),
        (41, 47), (45, 51), (48, 52), (49, 53), (50, 54),
    ]

    count = 0
    for i, shot in enumerate(measurements):
        logical_bits = []

        for (q1, q2) in pairs:
            # convert 1-based → 0-based logical qubit numbers
            logical_q1 = q1 - 1
            logical_q2 = q2 - 1

            # find positions of those qubits in measured_qubits
            try:
                idx1 = measured_qubits.index(logical_q1)
                idx2 = measured_qubits.index(logical_q2)
            except ValueError:
                # if either qubit wasn't measured, skip this pair
                continue

            pair = (shot[idx1], shot[idx2])

            if pair == (0, 0):
                logical_bits.append("0")
            elif pair == (1, 1):
                logical_bits.append("1")
            elif pair == (0, 1):
                logical_bits.append("1")
            elif pair == (1, 0):
                logical_bits.append("0")

        # make bitstring and integer
        bitstring = ''.join(logical_bits[::-1])
        number = int(bitstring, 2)

        QuantumShotResult.objects.create(
            bits=bitstring,
            number=number,
            batch_id=batch_id,
            shot_index=i
        )
        count += 1

    return count

def build_bitstream():
    """Concatenate all bits from DB into one long string."""
    all_bits = []
    for shot in QuantumShotResult.objects.all().order_by("id"):
        all_bits.append(shot.bits)
    return "".join(all_bits)

def md5_whitening(bits, block_size=512):
    """
    Apply MD5 hash to the bitstream in blocks to improve entropy.
    bits: list of 0/1
    block_size: number of bits per block
    """
    whitened = []
    n_blocks = (len(bits) + block_size - 1) // block_size
    for i in range(n_blocks):
        block = bits[i*block_size : (i+1)*block_size]
        byte_arr = int("".join(str(b) for b in block), 2).to_bytes((len(block)+7)//8, byteorder='big')
        h = hashlib.md5(byte_arr).digest()
        for byte in h:
            for j in range(8):
                whitened.append((byte >> (7-j)) & 1)
    return whitened


def von_neumann_whitening(bits):
    """Simple bias removal: output new bitstream from pairs."""
    whitened = []
    for i in range(0, len(bits)-1, 2):
        pair = bits[i], bits[i+1]
        if pair == (0, 1):
            whitened.append(0)
        elif pair == (1, 0):
            whitened.append(1)
        # discard (0,0) or (1,1)
    return whitened

def generate_numbers(bitstream, min_val, max_val):
    """Generate random numbers from a bitstream in range [min_val, max_val]."""
    n = max_val - min_val + 1
    bits_needed = math.ceil(math.log2(n))
    numbers = []

    i = 0
    while i + bits_needed <= len(bitstream):
        raw_bits = bitstream[i:i+bits_needed]
        number = int(raw_bits, 2)
        i += bits_needed

        # rejection sampling (avoid bias if 2^bits > n)
        if number < n:
            numbers.append(min_val + number)

    return numbers


def get_distributions():
    """Return frequency counts + totals for dice (0–6) and 4-bit (0–15)."""
    bitstream = build_bitstream()

    dice_rolls = generate_numbers(bitstream, 1, 6)
    four_bit_rolls = generate_numbers(bitstream, 0, 15)

    dist_d6 = Counter(dice_rolls)
    dist_d16 = Counter(four_bit_rolls)

    total_d6 = len(dice_rolls)
    total_d16 = len(four_bit_rolls)

    return dist_d6, dist_d16, total_d6, total_d16


def analyze_bitstream( n_splits=10):
    bitstream = build_bitstream()
    if isinstance(bitstream, str):
        bitstream = [int(b) for b in bitstream]

    total_len = len(bitstream)
    split_size = total_len // n_splits
    results = []

    for i in range(n_splits):
        start = i * split_size
        end = (i + 1) * split_size if i < n_splits - 1 else total_len
        chunk = bitstream[start:end]

        n0 = chunk.count(0)
        n1 = chunk.count(1)
        n = n0 + n1

        results.append({
            "split": i+1,
            "total": n,
            "zeros": n0,
            "ones": n1,
            "p0": n0 / n if n else 0,
            "p1": n1 / n if n else 0,
            "bias": abs(n1 / n - 0.5) if n else 0
        })

    # Prepare chart
    splits = [r['split'] for r in results]
    p0s = [r['p0'] for r in results]
    p1s = [r['p1'] for r in results]
    biases = [r['bias'] for r in results]

    fig, ax1 = plt.subplots(figsize=(10,5))
    ax1.bar([s-0.15 for s in splits], p0s, width=0.3, label='p0 (zeros)', color='skyblue')
    ax1.bar([s+0.15 for s in splits], p1s, width=0.3, label='p1 (ones)', color='salmon')
    ax1.set_xlabel('Split')
    ax1.set_ylabel('Proportion')
    ax1.set_ylim(0, 1)
    ax1.set_xticks(splits)
    ax1.legend(loc='upper left')

    ax2 = ax1.twinx()
    ax2.plot(splits, biases, color='green', marker='o', label='Bias')
    ax2.set_ylabel('Bias (|p1 - 0.5|)')
    ax2.legend(loc='upper right')
    plt.title('Bitstream Split Analysis')

    # Save chart to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    return {
        'chart': image_base64,
        'data': results
    }

def analyze_bitstream_extracted( n_splits=10):
    bitstream = build_bitstream()
    if isinstance(bitstream, str):
        bitstream = [int(b) for b in bitstream]
    bitstream = md5_whitening(bitstream , block_size=256)

    total_len = len(bitstream)
    split_size = total_len // n_splits
    results = []

    for i in range(n_splits):
        start = i * split_size
        end = (i + 1) * split_size if i < n_splits - 1 else total_len
        chunk = bitstream[start:end]

        n0 = chunk.count(0)
        n1 = chunk.count(1)
        n = n0 + n1

        results.append({
            "split": i+1,
            "total": n,
            "zeros": n0,
            "ones": n1,
            "p0": n0 / n if n else 0,
            "p1": n1 / n if n else 0,
            "bias": abs(n1 / n - 0.5) if n else 0
        })

    # Prepare chart
    splits = [r['split'] for r in results]
    p0s = [r['p0'] for r in results]
    p1s = [r['p1'] for r in results]
    biases = [r['bias'] for r in results]

    fig, ax1 = plt.subplots(figsize=(10,5))
    ax1.bar([s-0.15 for s in splits], p0s, width=0.3, label='p0 (zeros)', color='skyblue')
    ax1.bar([s+0.15 for s in splits], p1s, width=0.3, label='p1 (ones)', color='salmon')
    ax1.set_xlabel('Split')
    ax1.set_ylabel('Proportion')
    ax1.set_ylim(0, 1)
    ax1.set_xticks(splits)
    ax1.legend(loc='upper left')

    ax2 = ax1.twinx()
    ax2.plot(splits, biases, color='green', marker='o', label='Bias')
    ax2.set_ylabel('Bias (|p1 - 0.5|)')
    ax2.legend(loc='upper right')
    ax2.set_ylim(0.000, 0.035)
    plt.title('Bitstream Split Analysis')

    # Save chart to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    return {
        'chart': image_base64,
        'data': results
    }





# ----- Helper function to compute two-tailed p-value -----
def two_tailed_pvalue(z):
    """Two-tailed p-value from standard normal using erf."""
    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return 2 * (1 - cdf)

# ----- NIST Tests -----
def frequency_test(bits):
    """Monobit / Frequency Test"""
    n = len(bits)
    if n == 0:
        return 0.0
    s = 2 * sum(bits) - n
    z = abs(s) / math.sqrt(n)
    return two_tailed_pvalue(z)

def runs_test(bits):
    """Runs Test"""
    n = len(bits)
    if n == 0:
        return 0.0
    pi = float(sum(bits)) / n
    if abs(pi - 0.5) > (2.0 / math.sqrt(n)):
        return 0.0  # fails test immediately
    V = 1 + sum(bits[i] != bits[i+1] for i in range(n-1))
    z = abs(V - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(2 * n) * pi * (1 - pi))
    return two_tailed_pvalue(z)

def cumulative_sums_test(bits):
    """Cumulative Sums (Cusum) Test, forward"""
    n = len(bits)
    if n == 0:
        return 0.0
    s = [1 if b==1 else -1 for b in bits]
    S = np.cumsum(s)
    z = max(abs(S))
    return two_tailed_pvalue(z / math.sqrt(n))



# ----- Bitstream Analysis -----
def analyze_bitstream_nist():
    bitstream = build_bitstream()
    if isinstance(bitstream, str):
        bitstream = [int(b) for b in bitstream]

    bitstream = md5_whitening(bitstream , block_size=256)


    freq_p = frequency_test(bitstream)
    runs_p = runs_test(bitstream)
    cusum_p = cumulative_sums_test(bitstream)

    # Prepare chart (single point per test)
    tests = ['Frequency', 'Runs', 'Cusum']
    p_values = [freq_p, runs_p, cusum_p]

    fig, ax = plt.subplots(figsize=(8,4))
    ax.bar(tests, p_values, color=['skyblue','salmon','lightgreen','orange'])
    ax.axhline(0.01, color='red', linestyle='--', label='Significance 0.01')
    ax.set_ylabel('p-value')
    ax.set_ylim(0, 1)
    ax.set_title('NIST Test')
    ax.legend()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    chart_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return {"results": {"frequency": freq_p, "runs": runs_p, "cusum": cusum_p},
            "chart": chart_base64}



def poisson_cdf_safe(k, lam):
    """Compute Poisson CDF safely using logs to avoid overflow"""
    log_lam = math.log(lam)
    log_exp = -lam  # log(exp(-lam)) = -lam
    s = 0.0
    for i in range(k + 1):
        # log((lam^i * exp(-lam))/i!) = i*log(lam) - lam - log(i!)
        log_term = i * log_lam + log_exp - math.lgamma(i + 1)  # math.lgamma(i+1) = log(i!)
        s += math.exp(log_term)
    return min(1.0, s)


# --- Dieharder Approximations ---
def birthday_spacings_test(bitstream, m=512, n=128):
    k = int(np.ceil(math.log2(m)))
    if len(bitstream) < n * k:
        raise ValueError("Bitstream too short for Birthday Spacings Test")

    birthdays = []
    for i in range(n):
        chunk = bitstream[i * k: (i + 1) * k]
        val = int("".join(str(b) for b in chunk), 2)
        birthdays.append(val % m)

    birthdays.sort()
    spacings = [birthdays[i + 1] - birthdays[i] for i in range(n - 1)]
    collisions = len(spacings) - len(set(spacings))

    lam = n ** 3 / (4 * m)

    def poisson_cdf(k, lam):
        log_lam = math.log(lam)
        log_exp = -lam
        s = 0.0
        for i in range(k + 1):
            log_term = i * log_lam + log_exp - math.lgamma(i + 1)
            s += math.exp(log_term)
        return min(1.0, s)

    if collisions < lam:
        p_value = 2 * poisson_cdf(collisions, lam)
    else:
        p_value = 2 * (1 - poisson_cdf(collisions - 1, lam))

    return min(1.0, p_value)


def overlapping_permutations_test(bitstream, m=4):
    """
    Overlapping Permutations Test approximation
    """
    n = len(bitstream)
    if n < m:
        raise ValueError("Bitstream too short for Overlapping Permutations Test")

    num_perms = 2 ** m
    counts = [0] * num_perms

    for i in range(n - m + 1):
        idx = int("".join(str(b) for b in bitstream[i:i + m]), 2)
        counts[idx] += 1

    total_seq = n - m + 1
    expected = total_seq / num_perms

    # Chi-square statistic manually
    chi_sq = sum((c - expected) ** 2 / expected for c in counts)

    # Approximate p-value using chi-square distribution formula (without scipy)
    # Use gamma approximation: p-value ≈ 1 - gammainc(df/2, chi_sq/2)
    # Since we avoid external libs, use simple approximation:
    # p-value = exp(-chi_sq / 2)  (rough, only for small/medium df)
    p_value = min(1.0, math.exp(-chi_sq / 2))

    return p_value


def dieharder_tests_chart():
    """
    Run both Birthday Spacings and Overlapping Permutations and generate chart
    """
    bitstream = build_bitstream()
    bitstream = md5_whitening(bitstream)
    p_birthday = birthday_spacings_test(bitstream)
    p_overlap = overlapping_permutations_test(bitstream)

    results = {
        "birthday_spacings": p_birthday,
        "overlapping_permutations": p_overlap
    }

    # Generate chart
    tests = list(results.keys())
    p_values = [results[t] for t in tests]

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ['orange', 'purple']
    ax.bar(tests, p_values, color=colors)
    ax.axhline(0.01, color='red', linestyle='--', label='Significance 0.01')
    ax.set_ylim(0, 1)
    ax.set_ylabel('p-value')
    ax.set_title('Dieharder Approximation Tests')
    ax.legend()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    chart_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return {"results": results, "chart": chart_base64}


def next_bit_test_crossval(window_size=8, n_splits=5):

    bitstream = build_bitstream()
    # Ensure bitstream is a list of integers 0/1
    if isinstance(bitstream, str):
        bitstream = [int(b) for b in bitstream]

    total_len = len(bitstream)
    split_size = total_len // n_splits
    accuracies = []

    for i in range(n_splits):
        start = i * split_size
        end = (i + 1) * split_size if i < n_splits - 1 else total_len
        chunk = bitstream[start:end]

        if len(chunk) <= window_size:
            accuracies.append(0.5)  # fallback for too small chunk
            continue

        # Build dataset
        X = []
        y = []
        for j in range(len(chunk) - window_size):
            # Make sure this is a list of 0/1 integers
            window = chunk[j:j + window_size]
            X.append(window)
            y.append(chunk[j + window_size])

        X = np.array(X, dtype=int)  # shape (n_samples, window_size)
        y = np.array(y, dtype=int)  # shape (n_samples,)

        # Train-test split (70% train, 30% test)
        split_idx = int(len(X) * 0.7)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Train classifier
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)

        # Predict and compute accuracy
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        accuracies.append(acc)

    # Compute overall average
    avg_acc = np.mean(accuracies)

    # Create chart
    fig, ax = plt.subplots(figsize=(8, 4))
    folds = list(range(1, n_splits + 1))
    ax.bar(folds, accuracies, color='orange', label='Fold Accuracy')
    ax.axhline(0.5, color='red', linestyle='--', label='Random baseline 0.5')
    ax.axhline(0.55, color='green', linestyle='--', label='Pass threshold 0.55')
    ax.set_xticks(folds)
    ax.set_xlabel('Fold')
    ax.set_ylabel('Accuracy')
    ax.set_title('Next-Bit Test (5-Fold Cross-Validation)')
    ax.set_ylim(0, 1)
    ax.legend()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    chart_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Prepare results dict
    results_dict = {f"Fold {i + 1}": acc for i, acc in enumerate(accuracies)}
    results_dict["Average"] = avg_acc

    return {"results": results_dict, "chart": chart_base64}