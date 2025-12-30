@echo off
REM Launch the generator app on a network-visible interface for Windows users.
if "%GENERATOR_PORT%"=="" (set GENERATOR_PORT=8000)
python generator_app/app.py
