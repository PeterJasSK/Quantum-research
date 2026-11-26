#!/bin/bash
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/E1-redteam-inference-medium
python claimA.py --n 8 --inst 10 --snrs 3,6,10,14 --betas 0.5,0.71,1,1.41,2,4 --stbetas 0.5,1,2 --iat --out results/claimA_n8.json > logs/A_n8.log 2>&1
python claimA.py --n 10 --inst 6 --snrs 3,6,10,14 --betas 0.5,1,2 --stbetas 1 --out results/claimA_n10.json > logs/A_n10.log 2>&1
