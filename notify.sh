#!/bin/sh

. "$(dirname "$0")"/variables.cfg

if [ "$send_telegram" = "YES" ] ; then
  curl -s -o /dev/null --data chat_id=$telegram_chat_id --data parse_mode="Markdown" --data-urlencode "text=*$1*: $2" "https://api.telegram.org/bot$telegram_token/sendMessage"
fi

if [ "$send_pushbullet" = "YES" ] ; then
  curl -s -o /dev/null https://api.pushbullet.com/v2/pushes -u $pushbullet_token -d type="note" -d title="$1" -d body="$2" -X POST
fi
