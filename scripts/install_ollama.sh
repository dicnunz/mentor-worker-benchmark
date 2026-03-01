#!/usr/bin/env bash
set -euo pipefail

if command -v ollama >/dev/null 2>&1; then
  echo "Ollama already installed: $(ollama --version)"
  exit 0
fi

if command -v brew >/dev/null 2>&1; then
  echo "Installing Ollama via Homebrew..."
  brew install ollama
  echo "Done. Start it with: ollama serve"
else
  echo "Homebrew not found. Install Ollama manually from https://ollama.com/download"
  exit 1
fi
