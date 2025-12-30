#!/usr/bin/env bash
# Launch the generator app on a network-visible interface.
set -euo pipefail
streamlit run generator_app/app.py --server.address 0.0.0.0 --server.port 3000
