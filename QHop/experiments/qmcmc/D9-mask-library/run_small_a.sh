#!/bin/bash
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd "$(dirname "$0")"
for n in 6 8; do for s in 1 2 3 4 5 6 7 8 9 10; do python d9_run.py sk $n $s | tail -1; done; done
for s in 1 2 3 4 5; do python d9_run.py sk 10 $s | tail -1; done
