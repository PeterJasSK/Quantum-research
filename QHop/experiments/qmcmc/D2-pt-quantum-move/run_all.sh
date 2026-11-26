#!/bin/bash
# Reproduce all D2 runs (4 parallel workers, 1 thread each). Then: python analyze.py
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs results
{
  for k in 0 1 2 3 4; do echo "sk 12 $((1200+k))"; done
  for k in 0 1 2 3 4; do echo "sk 16 $((1600+k)) --noq"; echo "ea 16 $((500+k)) --noq"; echo "sk 18 $((1800+k)) --noq"; done
  for k in 0 1 2 3 4; do echo "ea 12 $((520+k))"; done
  for k in 0 1 2 3 4; do echo "sk 14 $((1400+k))"; done
} | xargs -P 2 -L 1 bash -c 'f=$0; n=$1; s=$2; [ -f results/${f}_n${n}_s${s}.json ] && grep -q wall_s results/${f}_n${n}_s${s}.json && exit 0; python run_instance.py "$0" "$@" > logs/${f}${n}_${s}.log 2>&1 || echo FAIL $f $n $s' 2>/dev/null
echo ALLDONE
