#!/bin/bash
# Build the shared Lambda layer
# Run from backend/layers/shared/
set -e

LAYER_DIR="python/lib/python3.12/site-packages"
rm -rf python
mkdir -p "$LAYER_DIR"

pip install -r requirements.txt -t "$LAYER_DIR" --no-cache-dir --quiet

echo "Layer built successfully at: $LAYER_DIR"
echo "Size: $(du -sh python | cut -f1)"
