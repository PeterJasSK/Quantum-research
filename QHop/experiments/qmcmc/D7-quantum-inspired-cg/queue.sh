#!/bin/bash
# two sequential slots (machine overloaded: max 2 own python processes)
cd /home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D7-quantum-inspired-cg
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
B=3.0
( for job in "sk 64" "sk 128" "sk 32"; do python run_exp.py $job $B >> results/run_${job// /}.log 2>&1; done; echo slotA_done >> results/queue.log ) &
( while pgrep -f "tune_pt.py ea" >/dev/null; do sleep 10; done
  for job in "ea 12" "ea 16" "ea 8"; do python run_exp.py $job $B >> results/run_${job// /}.log 2>&1; done; echo slotB_done >> results/queue.log ) &
wait
