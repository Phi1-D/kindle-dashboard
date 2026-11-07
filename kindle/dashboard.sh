#!/bin/sh
# Name: Start Dashboard
# Author: Phil
#
# Kindle scriptlet: copy this file into the Kindle's "documents" folder.
# It appears in the Library as "Start Dashboard". Tap it to start.
#
# To STOP the dashboard: hold the power button ~40 seconds until the Kindle restarts.
# The normal Kindle interface comes back after the restart; nothing starts automatically.

# ---- Settings -------------------------------------------------------------
URL="https://phi1-d.github.io/kindle-dashboard/YOUR-IMAGE-NAME.png"
REFRESH_MINS=30          # how often to fetch a new image
NIGHT_START=22           # stop refreshing from this hour (Kindle clock, UTC)...
NIGHT_END=6              # ...until this hour
# ---------------------------------------------------------------------------

DIR=/mnt/us/dashboard
IMG="$DIR/dash.png"
LOG="$DIR/dashboard.log"

# When tapped from the Library, relaunch in the background and return, so the
# loop survives the Kindle interface being stopped below.
if [ "$1" != "--loop" ]; then
  mkdir -p "$DIR"
  ( nohup sh "$0" --loop >"$LOG" 2>&1 & )
  exit 0
fi

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }

log "Dashboard starting"

# Stop the Kindle interface so it doesn't draw over the dashboard,
# and stop the screensaver from kicking in.
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
stop lab126_gui 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
sleep 3
eips -c

show_message() { eips -c; eips 2 20 "$1"; }

wait_for_wifi() {
  lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
  i=0
  while [ $i -lt 30 ]; do
    [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" = "CONNECTED" ] && return 0
    sleep 2; i=$((i + 1))
  done
  return 1
}

fetch() {
  rm -f "$IMG.tmp"
  # Try with certificate checks first; old Kindle certificate stores may be out of
  # date, so fall back to skipping the check (this only downloads a picture).
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 60 -o "$IMG.tmp" "$URL" || curl -kfsSL --max-time 60 -o "$IMG.tmp" "$URL"
  else
    wget -q -O "$IMG.tmp" "$URL" || wget -q --no-check-certificate -O "$IMG.tmp" "$URL"
  fi
  [ -s "$IMG.tmp" ] && mv "$IMG.tmp" "$IMG"
}

first=1
while true; do
  hour=$(date +%H | sed 's/^0//')
  if [ "$first" = 1 ] || { [ "$hour" -ge "$NIGHT_END" ] && [ "$hour" -lt "$NIGHT_START" ]; }; then
    if wait_for_wifi && fetch; then
      log "Fetched new image"
      eips -f -g "$IMG"      # -f = full refresh, clears e-ink ghosting
    else
      log "Fetch failed"
      if [ -s "$IMG" ]; then
        eips -f -g "$IMG"
        eips 1 1 "! offline"
      else
        show_message "Dashboard: no connection yet. Retrying..."
      fi
    fi
    first=0
  fi
  sleep $((REFRESH_MINS * 60))
done
