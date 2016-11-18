#!/bin/sh

curl -s -o /dev/null http://localhost:9091/transmission/web/ --max-time 60

if [ $? -eq 0 ] ; then
  echo "$(date): Transmission OK"
else
  SCRIPT_DIR="$(dirname "$0")"
  echo "$(date): Transmission not responding, restarting daemon"
  /usr/sbin/service transmission-daemon restart
  "$SCRIPT_DIR"/notify.sh "Transmission Watchdog" "Restarted the daemon"
fi
