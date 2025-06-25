import uuid
from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Person(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='recognition/uploads/faces/', blank=True, null=True)
    face_encoding = models.BinaryField() # store the image as binary bites

    def __str__(self):
        return self.name


class AttendanceRecord(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

class Session(models.Model):
    SESSION_STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('ended', 'Ended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=SESSION_STATUS_CHOICES, default='ongoing')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.subject} | {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('face_detected', 'Face Detected'),
        ('face_recognized', 'Face Recognized'),
        ('unknown_face', 'Unknown Face'),
        ('attendance_marked', 'Attendance Marked'),
        ('manual_override', 'Manual Override'),
        ('session_started', 'Session Started'),
        ('session_ended', 'Session Ended'),
    ]
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    session = models.ForeignKey(Session, related_name='events', on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True) # Optional: confidence, face_id, etc.

    def __str__(self):
        return f"{self.event_type} @ {self.timestamp.strftime('%H:%M:%S')} ({self.session.subject})"
    
