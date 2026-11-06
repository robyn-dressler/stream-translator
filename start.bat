set extra="cpu"
@echo off
where nvidia-smi >nul 2>&1
if errorlevel 1 goto start

nvidia-smi -L >nul 2>&1
if errorlevel 1 goto start

set extra="cuda"

:start
@echo on
uv sync --extra "%extra%" && uv run setup.py && uv run main.py --extra "%extra%"