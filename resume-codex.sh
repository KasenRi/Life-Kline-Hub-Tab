#!/usr/bin/env bash
set -euo pipefail

SESSION_ID="019cfeed-6ad1-7120-aa20-84b4d71b87e0"

cd /home/ribon
exec codex resume "$SESSION_ID" --yolo "$@"
