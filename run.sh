#!/bin/bash
# run.sh - Prepare and launch your container environment with display support (Wayland/X11)
# Updates only relevant variables in .env instead of overwriting the file.

ENV_FILE=".env"

# Helper function to add or update a key=value pair
update_env_var() {
    local key="$1"
    local value="$2"

    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        # Replace existing line
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        # Append if not found
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

# Helper function to remove a variable from .env if it exists
remove_env_var() {
    local key="$1"
    sed -i "/^${key}=.*/d" "$ENV_FILE" 2>/dev/null
}

# Ensure .env file exists
touch "$ENV_FILE"

# Step 1: Set VIDEO_GID
VIDEO_GID=$(getent group video | cut -d: -f3)
update_env_var "VIDEO_GID" "$VIDEO_GID"
echo "[✔] VIDEO_GID set to $VIDEO_GID in .env"

# Step 2: Detect display type
if [ -n "$WAYLAND_DISPLAY" ]; then
    echo "[✔] Detected Wayland display: $WAYLAND_DISPLAY"
    export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}

    # Remove old X11 vars
    remove_env_var "DISPLAY"

    # Update Wayland vars
    update_env_var "WAYLAND_DISPLAY" "$WAYLAND_DISPLAY"
    update_env_var "XDG_RUNTIME_DIR" "$XDG_RUNTIME_DIR"
    update_env_var "DISPLAY_TYPE" "wayland"
    update_env_var "SOCKET_PATH" "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"

else
    echo "[✔] Detected X11 display: $DISPLAY"
    xhost +local:docker

    # Remove old Wayland vars
    remove_env_var "WAYLAND_DISPLAY"
    remove_env_var "XDG_RUNTIME_DIR"
    remove_env_var "SOCKET_PATH"

    # Update X11 vars
    update_env_var "DISPLAY" "$DISPLAY"
    update_env_var "DISPLAY_TYPE" "x11"
fi

echo "[▶] Starting Docker Compose with display access..."
docker compose -f docker-compose.linux.yml up
