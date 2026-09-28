#!/usr/bin/env bash
# Send one line to Telegram from the head. Without a configuration it logs and succeeds, so no caller
# ever fails because alerting is not set up.
#
#   ops/notify.sh "text"
#
# Configuration, never in this repository: /home/mtxc/.config/dsv41/telegram.env (mode 600) with
#   TELEGRAM_BOT_TOKEN=123456:ABC...
#   TELEGRAM_CHAT_ID=-100123...
# The token goes to curl on stdin, not on its command line, so it does not show in the process list.
set -u
cfg=${DSV41_NOTIFY_ENV:-/home/mtxc/.config/dsv41/telegram.env}
text="[dsv41 $(hostname)] $*"
if [ ! -r "$cfg" ]; then echo "notify: $cfg missing, not sent: $text" >&2; exit 0; fi
# shellcheck source=/dev/null
. "$cfg"
[ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ] || { echo "notify: $cfg incomplete, not sent" >&2; exit 0; }
code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TELEGRAM_BOT_TOKEN" | \
  curl -s -m 20 -o /dev/null -w '%{http_code}' -K - --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" --data-urlencode "text=$text")
[ "$code" = 200 ] || echo "notify: Telegram answered $code for: $text" >&2
exit 0
