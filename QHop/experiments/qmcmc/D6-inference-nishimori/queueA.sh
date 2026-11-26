#!/bin/bash
# Sequential queue A (one python at a time). Waits for exp1 dense n=8 to finish.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
while pgrep -f "exp1_planted.py --family dense --n 8" >/dev/null; do sleep 15; done
for al in 0.5 2 1 1.5; do
  python exp1_planted.py --family dense --n 10 --alphas $al --snrs 0,3,6,10,14 --inst 6 --lean --out results/exp1_dense_n10_a$al.json > logs/exp1_dense_n10_a$al.log 2>&1
done
python exp1_planted.py --family dense --n 12 --alphas 0.5,2 --snrs 10 --inst 5 --betas 1,8 --lean --out results/exp1_dense_n12.json > logs/exp1_dense_n12.log 2>&1
