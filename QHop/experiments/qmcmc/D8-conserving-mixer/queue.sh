#!/bin/bash
# D8 sequential queue (coordinator rule: <=2 own python procs). Chain A waits for gaps cuau, chain B for gaps coulomb.
cd /home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D8-conserving-mixer
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common
A=$1; B=$2
( while kill -0 $A 2>/dev/null; do sleep 20; done
  python run_gaps.py sk 12 5 1 >> logs/gaps_sk.log 2>&1
  python run_pt.py cuau 5 > logs/pt_cuau.log 2>&1
  python run_pt.py sk 5 > logs/pt_sk.log 2>&1
  echo CHAIN_A_DONE >> logs/queue.log ) &
( while kill -0 $B 2>/dev/null; do sleep 20; done
  python run_symmetry.py > logs/symmetry.log 2>&1
  python run_pt.py coulomb 5 > logs/pt_coulomb.log 2>&1
  echo CHAIN_B_DONE >> logs/queue.log ) &
wait
