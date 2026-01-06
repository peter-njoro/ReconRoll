from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from .models import Session, Student, Event, FaceEncoding, AttendanceRecord
from .serializers import SessionSerializer, StudentSerializer
from .recognition_runner import active_recognition
import threading

class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to exempt CSRF checks for this viewset"""
        return csrf_exempt(super().dispatch)(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Automatically set the created_by user when creating a session"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start recognition for a session.
        
        Query params:
            - dev_mode: Set to 'true' to run in dev mode (uses main.py subprocess)
        """
        from .recognition_runner import run_recognition
        from django.utils import timezone
        
        session = self.get_object()
        dev_mode = request.query_params.get('dev_mode', 'false').lower() == 'true'
        
        # Check if session is already running
        if str(pk) in active_recognition:
            active_session = active_recognition[str(pk)]
            if active_session.get("thread") and active_session["thread"].is_alive():
                return Response(
                    {'error': f'Recognition is already running for session: {session.subject}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate session state
        if session.status == 'ended':
            return Response(
                {'error': f'Cannot start session - it has already ended'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if we have students in the class group (for non-dev mode)
        if not dev_mode and session.class_group and session.class_group.students.count() == 0:
            return Response(
                {'error': f'Class group has no students. Please add students first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if we have any face encodings in the database (for non-dev mode)
        if not dev_mode and not FaceEncoding.objects.exists():
            return Response(
                {'error': 'No face encodings found in database. Please enroll students first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stop_flag = threading.Event()
        
        try:
            # Start recognition in a separate thread
            t = threading.Thread(
                target=run_recognition,
                args=(str(pk),),
                kwargs={
                    'dev_mode': dev_mode,
                    'stop_flag': stop_flag
                },
                name=f"RecognitionThread-{pk}-{'dev' if dev_mode else 'prod'}"
            )
            t.daemon = True
            t.start()
            
            # Store the thread and stop flag for management
            active_recognition[str(pk)] = {
                "thread": t,
                "stop_flag": stop_flag,
                "started_at": timezone.now(),
                "mode": "dev" if dev_mode else "prod"
            }
            
            # Update session status
            session.status = 'ongoing'
            session.started_by = request.user if request.user.is_authenticated else None
            session.save()
            
            # Log the start event
            Event.objects.create(
                session=session,
                event_type='session_started',
                severity='info',
                message=f"Session started in {'DEV' if dev_mode else 'PRODUCTION'} mode via API"
            )
            
            return Response({
                'status': 'started',
                'session_id': pk,
                'subject': session.subject,
                'mode': 'dev' if dev_mode else 'prod',
                'message': f"Recognition started in {'DEV' if dev_mode else 'PRODUCTION'} mode"
            })
        
        except Exception as e:
            # Handle any errors during thread startup
            return Response(
                {'error': f'Failed to start recognition: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop recognition for a session"""
        from django.utils import timezone
        
        session = self.get_object()
        
        # Stop running thread/process if exists
        active = active_recognition.get(str(pk))
        if active:
            if active.get("stop_flag"):
                active["stop_flag"].set()
            
            # Also terminate subprocess if running in dev mode
            if "process" in active and active["process"]:
                active["process"].terminate()
            
            # Clean up
            active_recognition.pop(str(pk), None)
        
        if session.status != 'ended':
            session.status = 'ended'
            session.end_time = timezone.now()
            session.save()
            
            Event.objects.create(
                session=session,
                event_type='session_ended',
                severity='info',
                message="Session stopped via API"
            )
            
            return Response({
                'status': 'stopped',
                'session_id': pk,
                'subject': session.subject,
                'message': f"Session '{session.subject}' ended successfully"
            })
        else:
            return Response({
                'status': 'already_ended',
                'session_id': pk,
                'subject': session.subject,
                'message': f"Session was already ended"
            })
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        session = self.get_object()
        return Response({
            'id': session.id,
            'subject': session.subject,
            'status': session.status,
            'present_count': session.attendance_records.count(),
            'expected_count': session.class_group.students.count() if session.class_group else 0,
            'unknown_count': session.unidentified_faces.count(),
            'is_running': str(pk) in active_recognition and active_recognition[str(pk)].get('thread', {}).is_alive()
        })
    
    @action(detail=False, methods=['post'])
    def stop_all(self, request):
        """Stop all active recognition sessions (admin function)"""
        from django.utils import timezone
        
        stopped_count = 0
        for session_id, session_data in list(active_recognition.items()):
            try:
                session = Session.objects.get(id=session_id)
                if session_data.get("stop_flag"):
                    session_data["stop_flag"].set()
                    
                # Update session status
                if session.status == 'ongoing':
                    session.status = 'ended'
                    session.end_time = timezone.now()
                    session.save()
                    
                    Event.objects.create(
                        session=session,
                        event_type='session_ended',
                        severity='info',
                        message="Session stopped by admin via API"
                    )
                    
                stopped_count += 1
                
            except Session.DoesNotExist:
                pass
            
            # Clean up
            active_recognition.pop(session_id, None)
        
        return Response({
            'status': 'all_stopped',
            'stopped_count': stopped_count,
            'message': f"Stopped {stopped_count} active session(s)"
        })

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to exempt CSRF checks for this viewset"""
        return csrf_exempt(super().dispatch)(request, *args, **kwargs)