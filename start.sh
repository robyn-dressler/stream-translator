#!/bin/bash

EXTRA="cpu"

# Check for nvidia drivers and use CUDA if user turned it on
if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then
  EXTRA=$(python -c "import config; print('cuda' if config.enable_cuda else 'cpu')")

  # Checking if cuda toolkit is installed
  if [[ "$EXTRA" == "cuda" ]]; then
    if nvcc --version >/dev/null 2>&1; then
      echo "To use CUDA for translation, download and install the 12.x version: https://developer.nvidia.com/cuda-toolkit-archive"
      exit 1
    fi
  fi
fi

uv sync --extra "$EXTRA" && uv run --extra "$EXTRA" setup.py && ARGOS_DEVICE_TYPE="$EXTRA" uv run --extra "$EXTRA" main.py