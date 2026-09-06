"""T1 — the five obscure NP-complete problems on the T0 framework.

Each ``p<k>_<name>/`` package supplies ONLY its own math (``instance.py`` +
the best-known-classical algorithm in ``best_classical.py``) and inherits every
shared contract from :mod:`framework`. The thin driver files
(``classical_bruteforce.py`` / ``quantum_grover.py`` / ``best_classical.py``)
are ~identical across the five and delegate to :mod:`problems._drivers`.
"""
