#!/bin/sh
# keeps the bot alive: restarts it a few seconds after any crash
cd "$(dirname "$0")"
while true; do python3 main.py; sleep 5; done
