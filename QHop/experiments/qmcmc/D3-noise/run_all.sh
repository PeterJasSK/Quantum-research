#!/bin/bash
# D3 driver: exact DM sweeps. Run from D3-noise/.
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p logs
( for s in 100 101 102; do python sweep.py --family sk --n 6 --seed $s; python sweep.py --family sk --n 6 --seed $s --noises adsplit --eps 1e-3,1e-2; done ) > logs/n6a.log 2>&1 &
( for s in 103 104; do python sweep.py --family sk --n 6 --seed $s; python sweep.py --family sk --n 6 --seed $s --noises adsplit --eps 1e-3,1e-2; done ) > logs/n6b.log 2>&1 &
( for s in 100 101 102 103 104; do python sweep.py --family sk --n 8 --seed $s --ts 2 --c64 --noises dep --eps 1e-3,3e-3,1e-2; python sweep.py --family sk --n 8 --seed $s --ts 2 --c64 --noises ad --eps 1e-3,5e-3; done ) > logs/n8.log 2>&1 &
wait
