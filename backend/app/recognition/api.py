import threading
import base64
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import Session, Person, UnidentifiedFace, AttendanceSummary
from .serializers import SessionSerializer, PersonSerializer
from .recognition_runner import active_recognition, frame_queue


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Custom authentication that disables CSRF checks for the viewset"""

    def enforce_csrf(self, request):
        # Override DRF's CSRF enforcement to skip CSRF checks for API clients
        return None


def get_expected_count(session):
    """
    Get the expected count of people for a session.
    Priority: 1) Roster people count, 2) Manual expected_count field
    """
    if session.roster:
        return session.roster.people.count()
    return session.expected_count or 0


def get_present_records(session):
    return AttendanceSummary.objects.filter(
        session=session,
        status__in=['present', 'late']
    )


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def perform_create(self, serializer):
        """Automatically set the created_by user when creating a session"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def upload_frame(self, request, pk=None):
        """
        Upload a frame for processing (production mode).

        Accepts either:
        1. Multipart form data with 'frame' file (from frontend webcam)
        2. JSON with base64 'frame' data (legacy)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        session = self.get_object()

        # Check if session is running
        if session.status != 'in_progress':
            logger.warning(f"Upload frame rejected: session {pk} not in progress (status: {session.status})")
            return Response(
                {'error': 'Session is not running. Start the session first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if recognition thread is active
        if str(pk) not in active_recognition:
            logger.warning(f"Upload frame rejected: no active recognition thread for session {pk}")
            return Response(
                {'error': 'Recognition thread not active. Please restart the session.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if this is multipart form data (from frontend webcam)
            if request.FILES.get('frame'):
                logger.debug(f"Received multipart frame upload for session {pk}")
                
                # Read the uploaded file
                frame_file = request.FILES['frame']
                frame_bytes = frame_file.read()
                
                # Add to processing queue
                if not frame_queue.full():
                    frame_queue.put_nowait(bytes(frame_bytes))
                    logger.debug(f"Frame queued for session {pk}. Queue size: {frame_queue.qsize()}")
                    return Response({
                        'status': 'queued',
                        'queue_size': frame_queue.qsize(),
                        'message': 'Frame queued for processing'
                    })
                else:
                    logger.warning(f"Frame queue full for session {pk}")
                    return Response({
                        'status': 'queue_full',
                        'message': 'Processing queue is full. Frame skipped.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Otherwise, try JSON with base64 (legacy)
            frame_data = request.data.get('frame')
            if not frame_data:
                logger.debug(f"No frame data provided for session {pk}")
                return Response(
                    {'error': 'No frame data provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.debug(f"Received JSON/base64 frame upload for session {pk}")
            
            # Decode base64 to image
            if ',' in frame_data:
                # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
                frame_data = frame_data.split(',')[1]

            # Decode base64 to bytes
            frame_bytes = base64.b64decode(frame_data)

            # Add to processing queue
            if not frame_queue.full():
                frame_queue.put_nowait(bytes(frame_bytes))
                logger.debug(f"Frame queued for session {pk}. Queue size: {frame_queue.qsize()}")
                return Response({
                    'status': 'queued',
                    'queue_size': frame_queue.qsize(),
                    'message': 'Frame queued for processing'
                })
            else:
                logger.warning(f"Frame queue full for session {pk}")
                return Response({
                    'status': 'queue_full',
                    'message': 'Processing queue is full. Frame skipped.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        except Exception as e:
            logger.error(f"Failed to process frame for session {pk}: {e}", exc_info=True)
            return Response(
                {'error': f'Failed to process frame: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptSessionAuthentication]


# Backwards compatibility
StudentViewSet = PersonViewSet
