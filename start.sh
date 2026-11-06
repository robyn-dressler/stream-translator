#!/bin/bash

EXTRA="cpu"

if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then
  EXTRA="cuda"
fi

uv sync --extra "$EXTRA" && uv run setup.py && uv run main.py --extra "$EXTRA"