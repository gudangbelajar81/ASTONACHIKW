#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Installing frontend dependencies..."
npm install

echo "Starting frontend (next)"
npm run dev
