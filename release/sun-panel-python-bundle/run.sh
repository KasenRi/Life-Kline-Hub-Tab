#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x "./service_python/.venv/bin/python" ]; then
  ./install.sh
fi

PYTHONPATH=./service_python uv run --project service_python python -m sun_panel_python
