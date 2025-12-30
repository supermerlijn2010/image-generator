@echo off
REM Launch the labeler app on a network-visible interface for Windows users.
if "%LABELER_PORT%"=="" (set LABELER_PORT=8001)
python labeler_app/app.py
