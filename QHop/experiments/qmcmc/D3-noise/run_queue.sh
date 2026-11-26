#!/bin/bash
# D3 final queue (machine overloaded -> 2 sequential workers max). Run from D3-noise/.
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p logs
n6() { python sweep.py --family sk --n 6 --seed $1 --noises dep,ad; python sweep.py --family sk --n 6 --seed $1 --noises adgp,adtw,deph --eps 3e-4,2e-3,1e-2; }
n8() { python sweep.py --family sk --n 8 --seed $1 --ts 2 --c64 --noises dep --eps 1e-3,1e-2; }
( for s in 100 101 102; do n6 $s; done; for s in 100 102 104; do n8 $s; done
  python sweep.py --family sk --n 8 --seed 100 --ts 2 --c64 --noises ad --eps 2e-3 ) > logs/w1.log 2>&1 &
( for s in 103 104; do n6 $s; done; for s in 101 102 103 104; do python aer_fake.py --backend marrakesh --n 6 --seed $s; done
  for s in 101 103; do n8 $s; done
  python sweep.py --family sk --n 8 --seed 101 --ts 2 --c64 --noises ad --eps 2e-3 ) > logs/w2.log 2>&1 &
wait
