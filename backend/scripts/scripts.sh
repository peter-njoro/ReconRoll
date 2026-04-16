#!/bin/bash
set -e

# if running as root, setup permissions and drop privelages
if [ "$(id -u)" -eq 0 ]; then
    echo "Running as root to set up volumes ..."
    mkdir -p /vol/static /vol/media
    chown -R user:user /vol/static /vol/media
    chmod -R 775 /vol/static /vol/media

    echo "Dropping privileges to user..."
    exec gosu user "$0" "$@"
fi

# Normal excecution as user continues here
echo "Entrypoint script started..."
id

# Validate secret key   TO BE SET FOR PRODUCTION
# Uncomment the following lines to enforce secret key validation
# if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "default-dev-secret-key" ] || [ "$SECRET_KEY" = "must-be-set-for-production" ]; then
#     echo "ERROR: SECRET_KEY must be properly configured"
#     exit 1
# fi

cd /app

# Test webcam access
echo "Testing webcam device access..."
for device in /dev/video0 /dev/video1; do
    if [ -e "$device" ]; then
        if [ -r "$device" ] && [ -w "$device" ]; then
            echo "✓ $device exists and is readable/writable"
            # Try to open the device using v4l2-ctl if available
            if command -v v4l2-ctl >/dev/null 2>&1; then
                echo "Testing $device with v4l2-ctl:"
                v4l2-ctl --device=$device --all || echo "Failed to query $device"
            fi
        else
            echo "⚠ $device exists but has incorrect permissions"
            ls -l $device
        fi
    else
        echo "✗ $device does not exist"
    fi
done

# waiting for postgreSQL with proper connection check
echo "Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

# Use DB_HOST environment variable if set, otherwise use service name from DATABASE_URL or default to 'db'
DB_HOST="${DB_HOST:-db}"
if [ -n "$DATABASE_URL" ]; then
    # Extract hostname from DATABASE_URL (format: postgres://user:pass@host:port/db)
    DB_HOST=$(echo "$DATABASE_URL" | sed 's/postgres:\/\/[^@]*@\([^:]*\).*/\1/')
fi

echo "Connecting to database at: $DB_HOST"
echo "Using credentials - USER: $POSTGRES_USER, DB: $POSTGRES_DB"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if nc -z "$DB_HOST" 5432 2>/dev/null; then
        echo "✓ PostgreSQL port is open on $DB_HOST:5432"
        break
    else
        echo "Waiting for PostgreSQL port on $DB_HOST (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
    fi
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: PostgreSQL failed to respond on port 5432 after $MAX_RETRIES attempts"
    exit 1
fi

echo "PostgreSQL is reachable, proceeding with initialization..."

echo "Running Django management commands..."
echo "Making migrations"
python manage.py makemigrations

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser COMMENT IF YOU WANT A SUPERUSER I DON'T SEE THE POINT NOW TBH
if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "Creating superuser..."
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists():
    User.objects.create_superuser(
        username='${DJANGO_SUPERUSER_USERNAME}',
        email='${DJANGO_SUPERUSER_EMAIL}',
        password='${DJANGO_SUPERUSER_PASSWORD}'
    )
EOF
else
    echo "Superuser creation skipped."
fi

# If FRAME_FORWARDER is enabled, run webcam_stream.py in background
if [ "$FRAME_FORWARDER" = "true" ]; then
    echo "Starting webcam_stream.py for frame forwarding..."
    # Test webcam access before starting the stream
    WEBCAM_FOUND=0
    for device in /dev/video0 /dev/video1 /dev/video2 /dev/video3 /dev/video4; do
        if [ -e "$device" ]; then
            WEBCAM_FOUND=1
            echo "Found webcam device: $device"
        fi
    done
    
    if [ $WEBCAM_FOUND -eq 1 ]; then
        echo "Starting webcam stream in background..."
        # Start the stream with nohup so it continues even if connection drops
        FRAME_SERVER_URL="http://127.0.0.1:8000" nohup python recognition/webcam_stream.py >> /tmp/webcam_stream.log 2>&1 &
        WEBCAM_PID=$!
        echo $WEBCAM_PID > /tmp/webcam_stream.pid
        
        # Wait a moment to see if the process stays alive
        sleep 2
        if kill -0 $WEBCAM_PID 2>/dev/null; then
            echo "✓ Webcam stream started successfully (PID: $WEBCAM_PID)"
            echo "  Logs: tail -f /tmp/webcam_stream.log"
        else
            echo "⚠ Webcam stream failed to start properly"
            echo "  Check logs: cat /tmp/webcam_stream.log"
        fi
    else
        echo "⚠ No accessible webcam devices found, frame forwarding disabled"
        echo "  Available devices: $(ls /dev/video* 2>/dev/null || echo 'none')"
    fi
else
    echo "FRAME_FORWARDER is disabled, skipping webcam stream"
fi

echo "Starting uWSGI server using uwsgi.ini configuration..."
if [ "$DJANGO_MODE" = "production" ]; then
    exec uwsgi --ini /app/uwsgi.prod.ini
else
    exec uwsgi --ini /app/uwsgi.ini
fi
