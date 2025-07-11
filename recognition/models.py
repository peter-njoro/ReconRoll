import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

# Create your models here.

class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=254, unique=True, blank=True)
    course = models.CharField(max_length=100, blank=True)
    year_of_study = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.full_name} ({self.registration_number})"
    


class AttendanceRecord(models.Model):
    ATTENDANCE_SOURCE_CHOICES = [
        ('auto', 'Auto Face Recognition'),
        ('manual', 'Manual Marking'),
        ('override', 'Developer Override'),
    ]
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='attendance_entries')
    session = models.ForeignKey('Session', related_name='attendance_records', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=now)
    source = models.CharField(max_length=20, choices=ATTENDANCE_SOURCE_CHOICES, default='auto')
    source_event = models.ForeignKey('Event', on_delete=models.SET_NULL, null=True, blank=True)
    is_late = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'student')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student.full_name} - {self.session.subject} - {self.timestamp.strftime('%H:%M:%S')}"
    
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
    class_group = models.ForeignKey('ClassGroup', on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)

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
    
class FaceEncoding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='encodings')
    file_path = models.CharField(max_length=255, help_text="Path to the .npy file containing the face encoding.")
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about this encoding.")

    def __str__(self):
        return f"Encoding for {self.student.full_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
class ClassGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    students = models.ManyToManyField('Student', related_name='class_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def student_count(self):
        return self.students.count()

class UnidentifiedFace(models.Model):
    session = models.ForeignKey('Session', on_delete=models.CASCADE, related_name='unidentified_faces')
    image_path = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)