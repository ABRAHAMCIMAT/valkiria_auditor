#!/bin/bash
# Regenerates each Lambda service's requirements.lock, with hashes, inside the
# Lambda base image the services run on.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES="api comp2013 strandsagents langgraph crewai"
# Any image built on the Lambda base works, e.g. a local service image
IMAGE="${LAMBDA_IMAGE:-public.ecr.aws/lambda/python:3.12}"

docker run --rm --platform linux/arm64 --entrypoint /bin/sh -v "$BACKEND_DIR":/backend \
    "$IMAGE" -c "
        set -e
        pip install --quiet --target /tmp/uv uv==0.9.5
        for service in $SERVICES; do
            PYTHONPATH=/tmp/uv python -m uv pip compile --quiet --generate-hashes --no-header --python-version 3.12 \
                --only-binary :all: /backend/\$service/requirements.txt -o /backend/\$service/requirements.lock
            echo \"[INFO] Locked \$service\"
        done
    "
