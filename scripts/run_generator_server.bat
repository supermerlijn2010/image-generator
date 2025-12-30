@echo off
REM Launch the generator app on a network-visible interface for Windows users.
python -m streamlit run generator_app/app.py --server.address 0.0.0.0 --server.port 3000
