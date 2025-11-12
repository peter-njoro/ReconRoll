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

# waiting for postgreSQL
echo "Waiting for PostgreSQL to be ready..."
while ! nc -z db 5432; do
    sleep 0.1
done
echo "PostgreSQL is up and running!"

echo "Running Django management commands..."

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
    if [ -r "/dev/video0" ] || [ -r "/dev/video1" ]; then
        echo "Found accessible webcam device, starting stream..."
        python recognition/webcam_stream.py &
        WEBCAM_PID=$!
        # Wait a moment to see if the process stays alive
        sleep 2
        if kill -0 $WEBCAM_PID 2>/dev/null; then
            echo "Webcam stream started successfully"
        else
            echo "⚠ Webcam stream failed to start properly"
        fi
    else
        echo "⚠ No accessible webcam devices found, frame forwarding will not work"
        echo "Please check device permissions and container configuration"
    fi
fi


# echo "Starting uWSGI server..."
exec uwsgi --chdir /app \
    --module config.wsgi:application \
    --master \
    --processes 4 \
    --threads 2 \
    --http 0.0.0.0:8000 \
    --static-map /static=/vol/static \
    --static-map /media=/vol/media \
    --harakiri 0 \
    --http-timeout 600 \
    --socket-timeout 600 \
    --buffer-size=65535

