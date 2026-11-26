#!/bin/sh
# wait for n=12 seed 2 to finish, stop the n=12 job (seeds 3-5 cut for compute budget), then run the CPU-time bench
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
until grep -q "^2 3 {" results/c3_n12.log; do sleep 5; done
pkill -f "python c3_n12.py"
rm -f results/c3_bench.jsonl
for a in "sk 32" "sk 64" "ea 8" "ea 12"; do python c3_bench.py $a 2.0; done
echo BENCHDONE
