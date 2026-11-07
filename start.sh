#!/bin/bash

EXTRA="cpu"

if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then
  EXTRA=$(python -c "import config; print('cuda' if config.enable_cuda else 'cpu')")

  if [[ "$EXTRA" == "cuda" ]]; then
    python -c "import ctranslate2; print(ctranslate2.get_supported_compute_types('cuda'))" >/dev/null 2>&1
    if [ $? -eq 1 ]; then
      echo "To use CUDA for translation, download and install the 12.x version: https://developer.nvidia.com/cuda-toolkit-archive"
      exit 1
    fi
  fi
fi

uv sync --extra "$EXTRA" && uv run --extra "$EXTRA" setup.py && ARGOS_DEVICE_TYPE="$EXTRA" uv run --extra "$EXTRA" main.py