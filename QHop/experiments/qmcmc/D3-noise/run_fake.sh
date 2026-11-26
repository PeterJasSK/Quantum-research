#!/bin/bash
# D3 (v) driver: Aer density-matrix runs on fake backends, n=6, grid gamma {0.3,0.5} x t=2.
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p logs
( for s in 100 101 102 103 104; do python aer_fake.py --backend marrakesh --n 6 --seed $s; done ) > logs/fake_marrakesh.log 2>&1 &
( for s in 100 101 102 103 104; do python aer_fake.py --backend boston --n 6 --seed $s --nogauge; done ) > logs/fake_boston.log 2>&1 &
wait
