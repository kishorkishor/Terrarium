#!/bin/bash
# Session 4 (ablation asked for by the review): matched rule (trigger 77 %, stop 88 %, cap 300 s, rest 60 s)
# vs the learning controller, alternating 30 min blocks, lid 4 cm, same protocol as the 27 Sep evening.
# Stop the whole session early by creating data/STOP-SESSION.
cd /c/Users/kisho/Desktop/TERRARIUM
export PYTHONIOENCODING=utf-8
rm -f data/STOP data/STOP-SESSION
echo "MARK session 4 start: matched-rule ablation, lid 4 cm, water topped up" > data/lab-cmd.txt
log() { echo "$(date +%T) $1" >> data/lab-session4.out; }
for blk in 1 2; do
  log "matched rule block $blk"
  python tools/lab/logger.py --protocol baseline --minutes 30 --rule-lo 77 --rule-hi 88 --rule-cap 300 --rule-cool 60 >> data/lab-session4.out 2>&1
  [ -e data/STOP-SESSION ] && { log "session stopped"; exit 0; }; sleep 3
  log "learning block $blk"
  python tools/lab/brain_runner.py --minutes 30 >> data/lab-session4.out 2>&1
  [ -e data/STOP-SESSION ] && { log "session stopped"; exit 0; }; sleep 3
done
log "session 4 finished"
