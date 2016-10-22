#!/bin/sh

SCRIPT_DIR="$(dirname "$0")"
"$SCRIPT_DIR/notify.sh" "Download Complete" "$TR_TORRENT_NAME"
