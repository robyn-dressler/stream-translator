@echo off
where nvidia-smi >nul 2>&1
if errorlevel 1 goto cpu

nvidia-smi -L >nul 2>&1
if errorlevel 1 goto cpu

uv sync --extra cuda
if errorlevel 1 goto :eof
goto :start

:cpu
uv sync --extra cpu
if errorlevel 1 goto :eof

:start
@echo on
uv run setup.py && uv run main.py