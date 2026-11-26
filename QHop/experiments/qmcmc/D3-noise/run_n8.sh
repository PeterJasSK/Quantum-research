#!/bin/bash
# D3 n=8 exact DM (complex64), grid gamma {0.3,0.5} x t=2, two parallel streams.
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p logs
( for s in 100 102 104; do python sweep.py --family sk --n 8 --seed $s --ts 2 --c64 --noises dep --eps 1e-3,3e-3,1e-2; python sweep.py --family sk --n 8 --seed $s --ts 2 --c64 --noises ad --eps 2e-3; done ) > logs/n8a.log 2>&1 &
( for s in 101 103; do python sweep.py --family sk --n 8 --seed $s --ts 2 --c64 --noises dep --eps 1e-3,3e-3,1e-2; python sweep.py --family sk --n 8 --seed $s --ts 2 --c64 --noises ad --eps 2e-3; done ) > logs/n8b.log 2>&1 &
wait
