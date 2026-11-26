#!/bin/bash
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd "$(dirname "$0")"
for s in 6 7 8 9 10; do python d9_run.py sk 10 $s | tail -1; done
