#!/bin/bash
# Regenerates each agent's requirements.lock, with hashes, for the runtime's platform.
set -euo pipefail

AGENTCORE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker run --rm --platform linux/arm64 -v "$AGENTCORE_DIR":/agents \
    public.ecr.aws/docker/library/python:3.12-slim sh -c '
        pip install --quiet --root-user-action=ignore uv==0.9.5
        for dir in /agents/*_agent; do
            uv pip compile --quiet --generate-hashes --no-header --python-version 3.12 \
                --only-binary :all: "$dir/requirements.txt" -o "$dir/requirements.lock"
            echo "[INFO] Locked $(basename "$dir")"
        done
    '
