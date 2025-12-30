#!/usr/bin/env bash
# Launch the labeler app on a network-visible interface.
set -euo pipefail
export LABELER_PORT=${LABELER_PORT:-8001}
python labeler_app/app.py
