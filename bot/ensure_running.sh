#!/bin/sh
# Starts the bot (with auto-restart loop) unless the pid in /tmp/bot.pid is alive.
cd "$(dirname "$0")"
if [ -f /tmp/bot.pid ] && kill -0 "$(cat /tmp/bot.pid)" 2>/dev/null; then exit 0; fi
setsid nohup sh -c 'echo $$ > /tmp/bot.pid; exec ./run.sh' > /tmp/bot.log 2>&1 < /dev/null &
