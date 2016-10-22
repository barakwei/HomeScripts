#!/bin/sh

if curl http://localhost:9091/transmission/web/ --max-time 60 ; then
  echo "$(date): Transmission OK"
else
  SCRIPT_DIR="$(dirname "$0")"
  echo "$(date): Transmission not responding, restarting daemon"
  /usr/sbin/service transmission-daemon restart
  "$SCRIPT_DIR"/notify.sh "Transmission Watchdog" "Restated the daemon"
fi
