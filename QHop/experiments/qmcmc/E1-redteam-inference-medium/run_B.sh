#!/bin/bash
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/E1-redteam-inference-medium
python claimB.py 6 10 tune > logs/B_n6.log 2>&1
python claimB.py 8 10 tune > logs/B_n8.log 2>&1
python claimB.py 9 10 > logs/B_n9.log 2>&1
python claimB.py 10 10 tune > logs/B_n10.log 2>&1
python claimB.py 11 5 > logs/B_n11.log 2>&1
python claimB.py 12 3 > logs/B_n12.log 2>&1
