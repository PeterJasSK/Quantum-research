#!/bin/bash
# Sequential queue B (one python at a time). Waits for exp4 to finish.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
while pgrep -f "exp4_mrf.py" >/dev/null; do sleep 15; done
python exp2_tomo.py --R 3 --C 3 --views 2,3,4 --sigmas 0.25,0.5,1.0 --inst 6 --lean --out results/exp2_tomo_3x3.json > logs/exp2_3x3.log 2>&1
python exp3_genomics.py --P 10 --rs 0.8,0.9,0.95,0.98 --gs 30 --inst 6 --out results/exp3_gen_P10.json > logs/exp3_P10.log 2>&1
python exp1_planted.py --family sparse --n 8 --alphas 1,2 --snrs 0,6,10,14 --inst 6 --out results/exp1_sparse_n8.json > logs/exp1_sparse_n8.log 2>&1
