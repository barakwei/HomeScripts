#!/bin/sh

SCRIPT_DIR="$(dirname "$0")"
"$SCRIPT_DIR/notify.sh" "Download Complete" "$TR_TORRENT_NAME" >> $SCRIPT_DIR/logs/done_transmission.log 2>&1
