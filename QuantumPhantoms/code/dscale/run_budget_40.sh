#!/usr/bin/env bash
# D-SCALE LIVE run, 40-qubit version: one proof-of-concept job on real IBM hardware (backend picked automatically),
# then the tumours are grown from the measured quantum seed shapes and the page is built.
#
#   bash dscale/run_budget_40.sh                       # live: auto backend, submits directly (~11 QPU-s, cap 50 s)
#   DRYRUN=1 bash dscale/run_budget_40.sh              # pick backend + build + spend estimate, submit nothing
#   FAKE=FakeMarrakesh bash dscale/run_budget_40.sh    # local test of the same path (Aer, no QPU, not hardware)
#   RUN=../research_runs/dscale_live_40_<ts> JOB=<job id> bash dscale/run_budget_40.sh   # resume a submitted job
#   MAXQPU=50 SHOTS=2000 SRC=../research_runs/<f1 run>   # spend cap (QPU-seconds), shots, cohort to copy
#
# Uses the pre-saved QiskitRuntimeService() account (never a token). Results are labelled
# "hardware: <backend>, job <id>". Run from anywhere; it cd's to QuantumPhantoms/code.
set -u
B=40
PY=${PY:-/home/peter/anaconda3/bin/python3}
MAXQPU=${MAXQPU:-50}
SHOTS=${SHOTS:-2000}
FAKE=${FAKE:-}
JOB=${JOB:-}
DRYRUN=${DRYRUN:-0}
cd "$(dirname "$0")/.." || exit 1
SRC=${SRC:-../research_runs/qrng_aer_20261031-144146}
TS=$(date +%Y%m%d-%H%M%S)
RUN=${RUN:-../research_runs/dscale_live_${B}_$TS}
LOG=../research_runs/_dscale/logs_live_${B}_$TS
mkdir -p "$LOG"

EXTRA=""
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
echo "D-SCALE LIVE budget $B  |  $WHERE  |  cap $MAXQPU QPU-s, $SHOTS shots"
echo "cohort: $RUN  |  start $(date)"
if [ -z "$JOB" ]; then
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
[ $FAILED = 1 ] && echo "  a step failed: see $LOG/  (if the job was submitted, resume with RUN=$RUN JOB=<id> from $RUN/dscale/live/plan.json)"
echo "  outputs: $RUN/dscale/  (live/plan.json has the job id)   ../web/dscale_live_$B.html"
echo "  logs:    $LOG/"
echo "================================================================================"
