#!/bin/bash
# sequential n=12 queue (max 2 own python procs): waits for accept_curve to finish
cd /home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D5-surrogate
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
while pgrep -f "accept_curve.py" >/dev/null; do sleep 15; done
for i in 0 1 2; do
  ( time python sweep.py --n 12 --inst $i --fams a --rhos 0.1 0.3 0.6 --oracle_rhos 0.3 --light ) > results/log_n12_i$i.txt 2>&1
  ( time python tempered.py --n 12 --inst $i --fams a --rhos 0.1 0.3 0.6 ) > results/log_tempered12_i$i.txt 2>&1
done
echo QUEUE_DONE
