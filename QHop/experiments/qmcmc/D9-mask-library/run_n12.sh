#!/bin/bash
# queue: n=12 runs, one at a time per lane, started after the small-n lane finishes
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd "$(dirname "$0")"
lane=$1
while pgrep -f "run_small_$lane.sh" > /dev/null; do sleep 30; done
if [ "$lane" = b ]; then for s in 1 2 3 4 5; do python d9_run.py sk 12 $s --lite; done
else for s in 1 2 3 4 5; do python d9_run.py ea 12 $s --lite; done; fi
