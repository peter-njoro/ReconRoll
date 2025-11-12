#!/bin/bash
# run.sh - prepare and launch your container environment

# Step 1: Export host video group ID for container mapping
VIDEO_GID=$(getent group video | cut -d: -f3)
echo "VIDEO_GID=$VIDEO_GID" > .env
echo "[✔] VIDEO_GID set to $VIDEO_GID in .env"

# Step 2: Start Docker Compose
docker compose -f docker-compose.linux.yml up
