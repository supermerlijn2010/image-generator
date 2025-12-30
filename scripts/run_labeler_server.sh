#!/usr/bin/env bash
# Launch the labeler app on a network-visible interface.
set -euo pipefail
streamlit run labeler_app/app.py --server.address 0.0.0.0 --server.port 3001
