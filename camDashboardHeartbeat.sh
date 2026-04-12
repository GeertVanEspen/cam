#!/bin/bash

export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

#!/bin/bash
# ================================================
# camDashboardHeartbeat.sh
# Watchdog voor camDashboard.py
# Checkt elke 5 seconden of de live jpg's nog updaten
# ================================================

LOGFILE="/cam/camDashboardHeartbeat.log"
LIVE_DIR="/dev/shm/mjpeg"
KILL_PATTERN="camDashboard.py"
MAX_AGE=15          # seconden

echo "$(date '+%Y-%m-%d %H:%M:%S') HEARTBEAT gestart (max age ${MAX_AGE}s)" >> "$LOGFILE"

while true; do
  # Nieuwste van de 4 live jpg's pakken
  LATEST=$(ls -t "$LIVE_DIR"/cam6?.jpg 2>/dev/null | head -n1)

  if [ -n "$LATEST" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LATEST" 2>/dev/null || echo 0) ))

    if [ "$AGE" -gt "$MAX_AGE" ]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') WATCHDOG: live jpg ${AGE}s oud ($(basename "$LATEST")) → KILL & restart" >> "$LOGFILE"
      pkill -f "$KILL_PATTERN"
      # geef de wrapper even tijd om te herstarten
      sleep 60
    fi
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') WATCHDOG: GEEN live jpg gevonden → KILL" >> "$LOGFILE"
    pkill -f "$KILL_PATTERN"
    sleep 2
  fi

  sleep 5
  if [ -f "$LOGFILE" ] && [ $(stat -c %s "$LOGFILE" 2>/dev/null || echo 0) -gt 10485760 ]; then rm -f "$LOGFILE"; fi
done
