import logging 
from django.utils.timezone import now
from recognition.models import Event, Session, AttendanceRecord

logger  = logging.getLogger("recognition")

def record_event_or_log(
        request,
        session: Session,
        event_type: str,
        message: str,
        metadata: dict = None,
        severity: str = 'INFO'
):
    """Logs an event to the database or to system logs based on dev mode.
    
    Parameters:
    - request: Django HttpRequest object (used to check dev mode).
    - session: The session object the event is tied to.
    - event_type: e.g. 'face_recognized', 'attendance_marked'
    - message: Descriptive message for the event.
    - metadata: Dictionary with additional event data.
    - severity: 'INFO', 'WARNING', or 'ERROR'. Default is 'INFO'.
    """
    metadata = metadata or {}

    is_dev_mode = request.session.get("developer_mode", False)

    if is_dev_mode:
        log_method = getattr(logger, severity.lower(), logger.info)
        log_method(f"[DEV_MODE] {event_type} | {message} | Metadata={metadata}")
        return
    
    # Save event data to DB
    event = Event.objects.create(
        session=session,
        event_type=event_type,
        message=message,
        metadata=metadata,
    )

    # If it's an attendance event, auto-link it
    if event_type == 'attendance_marked':
        from recognition.models import Student

        face_id = metadata.get("face_id") or metadata.get("student_id")
        if face_id:
            try:
                student = Student.objects.get(id=face_id)
                AttendanceRecord.objects.create(
                    session=session,
                    student=student,
                    timestamp=now(),
                    source_event=event
                )
            except Student.DoesNotExist:
                logger.error(f"Attempted to mark attendance for unkown face ID: {face_id}")
                