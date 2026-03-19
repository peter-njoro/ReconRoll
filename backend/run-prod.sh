#!/bin/bash
# Run docker-compose.prod.yml with the correct env file for variable substitution
cd "$(dirname "$0")"

# Handle special commands
if [ "$1" = "webcam" ]; then
    shift  # Remove 'webcam' from arguments
    case "$1" in
        start)
            echo "🎥 Starting webcam stream daemon..."
            docker-compose --env-file .env.prod -f docker-compose.prod.yml exec reconroll \
                python manage.py webcam_stream_daemon --daemon
            ;;
        stop)
            echo "⏹️  Stopping webcam stream daemon..."
            docker-compose --env-file .env.prod -f docker-compose.prod.yml exec reconroll \
                python manage.py webcam_stream_daemon --stop
            ;;
        status)
            echo "📊 Checking webcam stream status..."
            docker-compose --env-file .env.prod -f docker-compose.prod.yml exec reconroll \
                python manage.py webcam_stream_daemon --status
            ;;
        logs)
            echo "📋 Webcam stream logs:"
            docker-compose --env-file .env.prod -f docker-compose.prod.yml exec reconroll \
                tail -f /tmp/webcam_stream.log
            ;;
        *)
            echo "Usage: $0 webcam {start|stop|status|logs}"
            exit 1
            ;;
    esac
else
    docker-compose --env-file .env.prod -f docker-compose.prod.yml "$@"
fi
