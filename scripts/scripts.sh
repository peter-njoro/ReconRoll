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
    python recognition/webcam_stream.py &
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

