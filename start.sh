#!/bin/bash

do_sync() {
  if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then
    uv sync --extra cuda
  else
    uv sync --extra cpu
  fi
}

do_sync && uv run setup.py && uv run main.py