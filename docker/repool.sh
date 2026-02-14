#!/bin/bash
cd "$(dirname "$0")"
docker-compose build && pkill -f "prefect worker.*Claude CICD" && nohup prefect worker start --pool "Claude CICD" &>/dev/null &
echo "✓ Rebuilt & restarted"
