#!/bin/bash
# Script to view FaceTrack logs in Docker

CONTAINER_NAME="facetrack-lite"
LOG_FILE="/var/log/uwsgi/reconroll.log"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== FaceTrack Log Viewer ===${NC}"
echo ""
echo "  --- Streaming ---"
echo "  1) Follow uWSGI logs (real-time)"
echo "  2) Follow Docker container logs"
echo ""
echo "  --- Snapshots ---"
echo "  3) Last 100 lines of uWSGI logs"
echo "  4) Last 100 lines of Docker logs"
echo ""
echo "  --- Errors & Warnings ---"
echo "  5) All errors (ERROR / Exception / Traceback)"
echo "  6) All warnings"
echo "  7) Last 50 errors with context (3 lines)"
echo "  8) HTTP 4xx / 5xx responses"
echo ""
echo "  --- Recognition ---"
echo "  9) Frame / queue activity"
echo "  10) Recognition events"
echo "  11) Attendance / roster events"
echo ""
echo "  --- Django ---"
echo "  12) Django request log (GET/POST/status)"
echo "  13) Database errors"
echo "  14) Authentication events (login/logout/403)"
echo ""
echo "  --- Utilities ---"
echo "  15) Count errors in log"
echo "  16) Tail log and highlight errors live"
echo "  17) Open shell in container"
echo "  18) Export last 500 lines to /tmp/facetrack-debug.log"
echo ""
read -p "Select option (1-18): " option

case $option in
    1)
        echo "Following uWSGI logs (Ctrl+C to stop)..."
        docker exec -it $CONTAINER_NAME tail -f $LOG_FILE
        ;;
    2)
        echo "Following Docker logs (Ctrl+C to stop)..."
        docker logs -f $CONTAINER_NAME
        ;;
    3)
        echo "Last 100 lines of uWSGI logs:"
        docker exec -it $CONTAINER_NAME tail -n 100 $LOG_FILE
        ;;
    4)
        echo "Last 100 lines of Docker logs:"
        docker logs --tail 100 $CONTAINER_NAME
        ;;
    5)
        echo -e "${RED}Errors / Exceptions / Tracebacks:${NC}"
        docker exec -it $CONTAINER_NAME grep -i -E "(error|exception|traceback|critical|fatal)" $LOG_FILE | tail -n 80
        ;;
    6)
        echo -e "${YELLOW}Warnings:${NC}"
        docker exec -it $CONTAINER_NAME grep -i "warning" $LOG_FILE | tail -n 50
        ;;
    7)
        echo -e "${RED}Last 50 errors with 3 lines of context:${NC}"
        docker exec -it $CONTAINER_NAME grep -i -n -E "(error|exception|traceback)" $LOG_FILE | tail -n 50
        echo ""
        echo "--- Full context (last 10 error occurrences) ---"
        docker exec -it $CONTAINER_NAME grep -i -A 3 -B 1 "traceback\|Exception" $LOG_FILE | tail -n 80
        ;;
    8)
        echo "HTTP 4xx / 5xx responses:"
        docker exec -it $CONTAINER_NAME grep -E "\" [45][0-9]{2} " $LOG_FILE | tail -n 50
        ;;
    9)
        echo "Frame / queue activity:"
        docker exec -it $CONTAINER_NAME grep -i -E "(frame|queue)" $LOG_FILE | tail -n 50
        ;;
    10)
        echo "Recognition events:"
        docker exec -it $CONTAINER_NAME grep -i "recognition" $LOG_FILE | tail -n 50
        ;;
    11)
        echo "Attendance / roster events:"
        docker exec -it $CONTAINER_NAME grep -i -E "(attendance|roster|present|absent)" $LOG_FILE | tail -n 50
        ;;
    12)
        echo "Django request log:"
        docker exec -it $CONTAINER_NAME grep -E "(GET|POST|PUT|PATCH|DELETE) /" $LOG_FILE | tail -n 60
        ;;
    13)
        echo -e "${RED}Database errors:${NC}"
        docker exec -it $CONTAINER_NAME grep -i -E "(OperationalError|ProgrammingError|IntegrityError|django.db)" $LOG_FILE | tail -n 40
        ;;
    14)
        echo "Authentication events:"
        docker exec -it $CONTAINER_NAME grep -i -E "(login|logout|403|unauthorized|forbidden|authentication)" $LOG_FILE | tail -n 40
        ;;
    15)
        echo "Error counts in log:"
        echo -n "  ERROR:     "; docker exec $CONTAINER_NAME grep -ic "error" $LOG_FILE
        echo -n "  WARNING:   "; docker exec $CONTAINER_NAME grep -ic "warning" $LOG_FILE
        echo -n "  EXCEPTION: "; docker exec $CONTAINER_NAME grep -ic "exception" $LOG_FILE
        echo -n "  TRACEBACK: "; docker exec $CONTAINER_NAME grep -ic "traceback" $LOG_FILE
        echo -n "  5xx:       "; docker exec $CONTAINER_NAME grep -cE "\" 5[0-9]{2} " $LOG_FILE
        echo -n "  4xx:       "; docker exec $CONTAINER_NAME grep -cE "\" 4[0-9]{2} " $LOG_FILE
        ;;
    16)
        echo "Tailing log with highlighted errors (Ctrl+C to stop)..."
        docker exec -it $CONTAINER_NAME tail -f $LOG_FILE | sed \
            -e "s/.*[Ee]rror.*/$(printf '\033[0;31m')&$(printf '\033[0m')/" \
            -e "s/.*[Ww]arning.*/$(printf '\033[1;33m')&$(printf '\033[0m')/" \
            -e "s/.*[Tt]raceback.*/$(printf '\033[0;31m')&$(printf '\033[0m')/"
        ;;
    17)
        echo "Opening shell in container..."
        docker exec -it $CONTAINER_NAME bash
        ;;
    18)
        OUTFILE="/tmp/facetrack-debug.log"
        echo "Exporting last 500 lines to $OUTFILE..."
        docker exec $CONTAINER_NAME tail -n 500 $LOG_FILE > "$OUTFILE"
        echo "Done. View with: cat $OUTFILE"
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
