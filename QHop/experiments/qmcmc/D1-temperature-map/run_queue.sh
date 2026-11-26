#!/bin/bash
# Runs all jobs in logs/jobs.txt, 3 in parallel, 2 BLAS threads each.
cd "$(dirname "$0")"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
xargs -P 2 -L 1 -I{} bash -c '[ -f logs/skip ] || python3 {} >> logs/queue.log 2>&1' < logs/jobs.txt
