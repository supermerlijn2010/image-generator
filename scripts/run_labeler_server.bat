@echo off
REM Launch the labeler app on a network-visible interface for Windows users.
python -m streamlit run labeler_app/app.py --server.address 0.0.0.0 --server.port 3001
