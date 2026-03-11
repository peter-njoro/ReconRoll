import threading
import cv2
import numpy as np
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
from .models import Session, Person, Event, AttendanceSummary, UnidentifiedFace
from .serializers import SessionSerializer, PersonSerializer, EventSerializer
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

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get current status of a session"""
        session = self.get_object()
        active_data = active_recognition.get(str(pk), {})
        thread = active_data.get('thread')
        is_running = bool(thread and thread.is_alive())

        return Response({
            'id': session.id,
            'name': session.name,
            'status': session.status,
            'present_count': get_present_records(session).count(),
            'expected_count': get_expected_count(session),
            'unknown_count': session.unidentified_faces.count(),
            'is_running': is_running
        })

    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Get all events for a session"""
        session = self.get_object()
        events = Event.objects.filter(session=session).order_by('-timestamp')[:50]
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def present(self, request, pk=None):
        """Get all present people for a session"""
        session = self.get_object()
        present_people = Person.objects.filter(
            attendance_records__session=session,
            attendance_records__status__in=['present', 'late']
        ).distinct()
        serializer = PersonSerializer(present_people, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def absent(self, request, pk=None):
        """Get all absent people for a session"""
        session = self.get_object()
        
        # Get expected people from roster if available
        if session.roster:
            expected_people = session.roster.people.all()
        else:
            return Response([])

        present_ids = set(
            get_present_records(session).values_list('person_id', flat=True)
        )
        absent_people = expected_people.exclude(id__in=present_ids)
        serializer = PersonSerializer(absent_people, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get attendance progress for a session"""
        session = self.get_object()
        present_count = get_present_records(session).count()
        expected_count = get_expected_count(session)
        unidentified_count = session.unidentified_faces.count()
        attendance_percentage = round((present_count / expected_count * 100), 2) if expected_count > 0 else 0

        return Response({
            'present_count': present_count,
            'expected_count': expected_count,
            'unidentified_count': unidentified_count,
            'attendance_percentage': attendance_percentage,
            'total_expected': expected_count,
            'unknown_count': unidentified_count
        })

    @action(detail=True, methods=['get'])
    def unidentified(self, request, pk=None):
        """Get all unidentified faces for a session"""
        session = self.get_object()
        unidentified_faces = UnidentifiedFace.objects.filter(session=session).order_by('-timestamp')

        return Response([
            {
                'id': face.id,
                'cropped_face': request.build_absolute_uri(face.cropped_face.url) if face.cropped_face else None,
                'full_frame': request.build_absolute_uri(face.full_frame.url) if face.full_frame else None,
                'timestamp': face.timestamp.isoformat() if face.timestamp else None
            }
            for face in unidentified_faces
        ])

    @action(detail=True, methods=['post'])
    def upload_frame(self, request, pk=None):
        """
        Upload a frame for processing (production mode).

        Expected payload:
        {
            "frame": "base64_encoded_image_data"
        }
        """
        session = self.get_object()

        # Check if session is running
        if session.status != 'in_progress':
            return Response(
                {'error': 'Session is not running. Start the session first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if recognition thread is active
        if str(pk) not in active_recognition:
            return Response(
                {'error': 'Recognition thread not active. Please restart the session.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get base64 frame data
            frame_data = request.data.get('frame')
            if not frame_data:
                return Response(
                    {'error': 'No frame data provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Decode base64 to image
            if ',' in frame_data:
                # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
                frame_data = frame_data.split(',')[1]

            # Decode base64 to bytes
            frame_bytes = base64.b64decode(frame_data)

            # Add to processing queue
            # The frame is already in JPEG format, so we can add it directly
            if not frame_queue.full():
                frame_queue.put(frame_bytes)
                return Response({
                    'status': 'queued',
                    'queue_size': frame_queue.qsize(),
                    'message': 'Frame queued for processing'
                })
            else:
                return Response({
                    'status': 'queue_full',
                    'message': 'Processing queue is full. Frame skipped.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        except Exception as e:
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
