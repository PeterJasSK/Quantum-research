#!/usr/bin/env bash
# D-SCALE LIVE run, 100-qubit version, ~4x QPU (~60 s real): the cohort itself is rolled on the QPU (F1 circuits +
# CHSH, one job; S <= 2 rejects the draw), then the D-SCALE job (more shots, 24 DFE stabilizers) runs on the SAME
# automatically picked backend, the tumours are grown from the measured seed shapes and the page is built.
#
#   bash dscale/run_budget_100.sh                       # live: auto backend, submits directly (~11 QPU-s, cap 50 s)
#   DRYRUN=1 bash dscale/run_budget_100.sh              # pick backend + build + spend estimate, submit nothing
#   FAKE=FakeMarrakesh bash dscale/run_budget_100.sh    # local test of the same path (Aer, no QPU, not hardware)
#   RUN=../research_runs/dscale_live_100_<ts> JOB=<job id> bash dscale/run_budget_100.sh   # resume the D-SCALE job
#   RUN=../research_runs/dscale_live_100_<ts> ROLLJOB=<job id> bash dscale/run_budget_100.sh   # resume the cohort roll
#   MAXQPU=45 SHOTS=4000 MDFE=24      # estimated QPU-s for BOTH jobs (45 est ~ 60 s real), shots, DFE count
#   ROLL=0 SRC=../research_runs/<f1 run>   # old mode: copy a simulated cohort instead of rolling it on the QPU
#
# Uses the pre-saved QiskitRuntimeService() account (never a token). Results are labelled
# "hardware: <backend>, job <id>". Run from anywhere; it cd's to QuantumPhantoms/code.
set -u
B=100
PY=${PY:-/home/peter/anaconda3/bin/python3}
MAXQPU=${MAXQPU:-45}
SHOTS=${SHOTS:-4000}
MDFE=${MDFE:-24}
ROLL=${ROLL:-1}
FAKE=${FAKE:-}
JOB=${JOB:-}
DRYRUN=${DRYRUN:-0}
cd "$(dirname "$0")/.." || exit 1
SRC=${SRC:-../research_runs/qrng_aer_20261031-144146}
TS=$(date +%Y%m%d-%H%M%S)
RUN=${RUN:-../research_runs/dscale_live_${B}_$TS}
LOG=../research_runs/_dscale/logs_live_${B}_$TS
mkdir -p "$LOG"

EXTRA="--m-dfe $MDFE"
[ "$ROLL" = 1 ] && EXTRA="$EXTRA --roll-cohort"
[ -n "${ROLLJOB:-}" ] && EXTRA="$EXTRA --roll-job $ROLLJOB"     # resume an interrupted cohort roll (same RUN)
[ -n "$FAKE" ] && EXTRA="$EXTRA --fake $FAKE"
[ -n "$JOB" ] && EXTRA="$EXTRA --job $JOB"
[ "$DRYRUN" = 1 ] && EXTRA="$EXTRA --dry-run"

STEPS=3; [ "$DRYRUN" = 1 ] && STEPS=1
STEP=0; T0=$(date +%s); declare -a SUMMARY; FAILED=0
hms() { printf '%02d:%02d:%02d' $(($1/3600)) $(($1%3600/60)) $(($1%60)); }
step() {                         # step "<title>" <log name> <command...>
  local title=$1 name=$2; shift 2
  STEP=$((STEP+1))
  local t=$(date +%s)
  echo
  echo "================================================================================"
  echo "[$STEP/$STEPS] $(date +%H:%M:%S)  budget $B  $title"
  echo "      total elapsed $(hms $((t-T0)))   log: $LOG/$name.log"
  echo "================================================================================"
  "$@" 2>&1 | grep --line-buffered -v "Warning" | tee "$LOG/$name.log"
  local rc=${PIPESTATUS[0]} dt=$(($(date +%s)-t))
  echo "--> [$STEP/$STEPS] done in $(hms $dt), exit $rc"
  SUMMARY+=("[$STEP/$STEPS] $(printf '%-40s' "$title") exit $rc  $(hms $dt)")
  [ $rc -ne 0 ] && FAILED=1
  return $rc
}

if [ -n "$FAKE" ]; then WHERE="LOCAL FAKE $FAKE (not hardware)"; else WHERE="real hardware, auto backend"; fi
echo "D-SCALE LIVE budget $B  |  $WHERE  |  cap $MAXQPU QPU-s (both jobs), $SHOTS shots, cohort rolled on QPU: $ROLL"
echo "cohort: $RUN  |  start $(date)"
if [ -z "$JOB" ] && [ "$ROLL" = 1 ]; then
  mkdir -p "$RUN"                    # empty cohort dir: the QPU rolls the parameters
elif [ -z "$JOB" ]; then
  mkdir -p "$RUN"
  cp "$SRC/cohort_params.json" "$SRC/quantum_run.json" "$RUN/" || { echo "cannot copy cohort from $SRC"; exit 1; }
fi

step "quantum job: pick backend, submit, analyse" live \
     $PY -m dscale.live --run "$RUN" --budget $B --max-qpu-seconds $MAXQPU --shots $SHOTS $EXTRA
if [ "$DRYRUN" != 1 ] && [ $FAILED = 0 ]; then
  step "grow tiles from the measured seeds" tiles $PY -m imaging.build_tiles --run "$RUN"
  step "web page with D-SCALE panel"        web   $PY -m f3_web.build_web --run "$RUN" --out ../web/dscale_live_$B.html
fi

echo
echo "================================================================================"
echo "D-SCALE LIVE budget $B finished $(date +%H:%M:%S), total $(hms $(($(date +%s)-T0)))"
printf '  %s\n' "${SUMMARY[@]}"
[ $FAILED = 1 ] && echo "  a step failed: see $LOG/  (if the job was submitted, resume with RUN=$RUN ROLLJOB=<id from $RUN/roll_job.json> or JOB=<id from $RUN/dscale/live/plan.json>)"
echo "  outputs: $RUN/dscale/  (live/plan.json has the job id)   ../web/dscale_live_$B.html"
echo "  logs:    $LOG/"
echo "================================================================================"
