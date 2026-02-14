import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Person(models.Model):
    """Individuals who will be recognized by the system"""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    identification_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Student ID, Employee ID, etc."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='persons_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'persons'
        verbose_name = 'Person'
        verbose_name_plural = 'Persons'
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.identification_number})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class FaceEncoding(models.Model):
    """Stores facial recognition encodings for persons"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='face_encodings',
        db_index=True
    )
    encoding = models.BinaryField(
        blank=True,
        null=True,
        help_text="Serialized numpy array of face encoding"
    )
    image_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to the original image file"
    )
    image_hash = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        help_text="SHA-256 hash for duplicate detection"
    )
    quality_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        blank=True,
        null=True,
        help_text="Image quality metric (0-1)"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary encoding for this person"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'face_encodings'
        verbose_name = 'Face Encoding'
        verbose_name_plural = 'Face Encodings'
        indexes = [
            models.Index(fields=['person', 'is_primary']),
        ]

    def __str__(self):
        return f"Encoding for {self.person.get_full_name()} (Primary: {self.is_primary})"

    def save(self, *args, **kwargs):
        # If this is set as primary, unset other primary encodings for this person
        if self.is_primary:
            FaceEncoding.objects.filter(
                person=self.person,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)


class Session(models.Model):
    """Represents an attendance/recognition session"""

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    session_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="e.g., class, meeting, event"
    )
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(blank=True, null=True)
    expected_count = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Expected number of attendees"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sessions_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sessions'
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    def get_attendance_stats(self):
        """Calculate attendance statistics for this session"""
        expected = self.expected_persons.count()
        present = self.recognitions.count()
        absent = expected - present

        return {
            'expected': expected,
            'present': present,
            'absent': absent,
            'attendance_rate': (present / expected * 100) if expected > 0 else 0
        }


class SessionExpectedPerson(models.Model):
    """Links persons expected to attend a session"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='expected_persons',
        db_index=True
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='expected_sessions',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'session_expected_persons'
        verbose_name = 'Session Expected Person'
        verbose_name_plural = 'Session Expected Persons'
        unique_together = ['session', 'person']

    def __str__(self):
        return f"{self.person.get_full_name()} expected at {self.session.name}"


class Recognition(models.Model):
    """Records each recognition event during a session"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='recognitions',
        db_index=True
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='recognitions',
        db_index=True
    )
    recognized_at = models.DateTimeField(default=timezone.now, db_index=True)
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        blank=True,
        null=True,
        help_text="Recognition confidence (0-1)"
    )
    image_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to the captured image"
    )
    face_encoding_used = models.ForeignKey(
        FaceEncoding,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recognitions'
    )
    is_verified = models.BooleanField(
        default=True,
        help_text="Manual verification flag"
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'recognitions'
        verbose_name = 'Recognition'
        verbose_name_plural = 'Recognitions'
        unique_together = ['session', 'person']
        ordering = ['-recognized_at']

    def __str__(self):
        return f"{self.person.get_full_name()} recognized at {self.session.name}"


class AttendanceSummary(models.Model):
    """Precomputed attendance status for quick queries"""

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        db_index=True
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True
    )
    marked_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_summary'
        verbose_name = 'Attendance Summary'
        verbose_name_plural = 'Attendance Summaries'
        unique_together = ['session', 'person']

    def __str__(self):
        return f"{self.person.get_full_name()} - {self.session.name}: {self.status}"


# Signal handlers for auto-updating attendance summary
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=Recognition)
def update_attendance_on_recognition(sender, instance, created, **kwargs):
    """Update attendance summary when a person is recognized"""
    if created:
        # Determine if late based on session start time
        is_late = instance.recognized_at > instance.session.start_time

        AttendanceSummary.objects.update_or_create(
            session=instance.session,
            person=instance.person,
            defaults={
                'status': 'late' if is_late else 'present',
                'marked_at': instance.recognized_at
            }
        )


@receiver(post_save, sender=SessionExpectedPerson)
def create_absent_attendance_record(sender, instance, created, **kwargs):
    """Create absent attendance record for expected persons"""
    if created:
        # Check if person was already recognized
        recognition_exists = Recognition.objects.filter(
            session=instance.session,
            person=instance.person
        ).exists()

        if not recognition_exists:
            AttendanceSummary.objects.get_or_create(
                session=instance.session,
                person=instance.person,
                defaults={'status': 'absent'}
            )


@receiver(post_delete, sender=Recognition)
def mark_as_absent_on_recognition_delete(sender, instance, **kwargs):
    """Mark as absent when recognition is deleted"""
    # Check if person is expected in this session
    is_expected = SessionExpectedPerson.objects.filter(
        session=instance.session,
        person=instance.person
    ).exists()

    if is_expected:
        AttendanceSummary.objects.update_or_create(
            session=instance.session,
            person=instance.person,
            defaults={'status': 'absent', 'marked_at': None}
        )
    else:
        # If not expected, delete the attendance record
        AttendanceSummary.objects.filter(
            session=instance.session,
            person=instance.person
        ).delete()
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
    student = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.event_type} @ {self.timestamp.strftime('%H:%M:%S')} ({self.session.name})"


class UnidentifiedFace(models.Model):
    session = models.ForeignKey('Session', on_delete=models.CASCADE, related_name='unidentified_faces')
    cropped_face = models.ImageField(upload_to="unidentified/cropped/", null=True, blank=True)
    full_frame = models.ImageField(upload_to="unidentified/full/", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    encoding = models.BinaryField(null=True, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    confidence = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Unidentified face at {self.timestamp}"
