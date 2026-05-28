#!/usr/bin/env bash
# Simple deploy script (CI) - builds and pushes docker images (adjust registry)
set -e
IMAGE=registry.example.com/jarvis/web:latest
docker build -t "$IMAGE" .
# docker push "$IMAGE"
echo "Built $IMAGE (push step commented out)."