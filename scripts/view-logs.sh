#!/bin/bash
# Script to view FaceTrack logs in Docker

CONTAINER_NAME="facetrack-lite"

echo "=== FaceTrack Log Viewer ==="
echo ""
echo "Available options:"
echo "  1) Follow uWSGI logs (real-time)"
echo "  2) View last 100 lines of uWSGI logs"
echo "  3) Follow Docker container logs"
echo "  4) View last 100 lines of Docker logs"
echo "  5) Search logs for 'frame' or 'queue'"
echo "  6) Search logs for 'recognition'"
echo "  7) Open shell in container"
echo ""
read -p "Select option (1-7): " option

case $option in
    1)
        echo "Following uWSGI logs (Ctrl+C to stop)..."
        docker exec -it $CONTAINER_NAME tail -f /var/log/uwsgi/reconroll.log
        ;;
    2)
        echo "Last 100 lines of uWSGI logs:"
        docker exec -it $CONTAINER_NAME tail -n 100 /var/log/uwsgi/reconroll.log
        ;;
    3)
        echo "Following Docker logs (Ctrl+C to stop)..."
        docker logs -f $CONTAINER_NAME
        ;;
    4)
        echo "Last 100 lines of Docker logs:"
        docker logs --tail 100 $CONTAINER_NAME
        ;;
    5)
        echo "Searching for 'frame' or 'queue' in logs:"
        docker exec -it $CONTAINER_NAME grep -i -E "(frame|queue)" /var/log/uwsgi/reconroll.log | tail -n 50
        ;;
    6)
        echo "Searching for 'recognition' in logs:"
        docker exec -it $CONTAINER_NAME grep -i "recognition" /var/log/uwsgi/reconroll.log | tail -n 50
        ;;
    7)
        echo "Opening shell in container..."
        docker exec -it $CONTAINER_NAME bash
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
