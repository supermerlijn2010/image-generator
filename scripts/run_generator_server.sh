#!/usr/bin/env bash
# Launch the generator app on a network-visible interface.
set -euo pipefail
export GENERATOR_PORT=${GENERATOR_PORT:-8000}
python generator_app/app.py
