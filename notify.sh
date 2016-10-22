#!/bin/sh

. "$(dirname "$0")"/notify.cfg

if [ "$send_telegram" = "YES" ] ; then
  curl --data chat_id=$telegram_chat_id --data-urlencode "text=$1: $2" "https://api.telegram.org/bot$telegram_token/sendMessage"
fi

if [ "$send_pushbullet" = "YES" ] ; then
  curl https://api.pushbullet.com/v2/pushes -u $pushbullet_token -d type="note" -d title="$1" -d body="$2" -X POST
fi
