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


class Roster(models.Model):
    """A reusable set of expected people for sessions"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    people = models.ManyToManyField(
        Person,
        related_name='rosters',
        blank=True,
        help_text="People expected to be in this roster"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rosters_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rosters'
        verbose_name = 'Roster'
        verbose_name_plural = 'Rosters'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.people.count()} people)"


class RosterAttendance(models.Model):
    """Tracks attendance status for people in a roster during a session"""

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roster = models.ForeignKey(
        Roster,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        db_index=True,
        help_text="Roster this attendance record belongs to"
    )
    session = models.ForeignKey(
        'Session',
        on_delete=models.CASCADE,
        related_name='roster_attendance_records',
        db_index=True,
        help_text="Session this attendance is for"
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='roster_attendance_records',
        db_index=True,
        help_text="Person from the roster"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True,
        help_text="Attendance status"
    )
    marked_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Time when person was marked/recognized"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roster_attendance'
        verbose_name = 'Roster Attendance'
        verbose_name_plural = 'Roster Attendances'
        unique_together = ['roster', 'session', 'person']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['roster', 'session']),
        ]

    def __str__(self):
        return f"{self.person.get_full_name()} - {self.roster.name} ({self.session.name}): {self.status}"


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
    roster = models.ForeignKey(
        Roster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
        help_text="Roster of expected people for this session"
    )
    session_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="e.g., class, meeting, event (deprecated, use roster instead)"
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


# Signal handlers for auto-updating attendance
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=Recognition)
def update_attendance_on_recognition(sender, instance, created, **kwargs):
    """Update attendance records when a person is recognized"""
    if created:
        # Determine if late based on session start time
        is_late = instance.recognized_at > instance.session.start_time
        status = 'late' if is_late else 'present'

        # Update AttendanceSummary for backward compatibility
        AttendanceSummary.objects.update_or_create(
            session=instance.session,
            person=instance.person,
            defaults={
                'status': status,
                'marked_at': instance.recognized_at
            }
        )
        
        # Update RosterAttendance if session has a roster
        if instance.session.roster:
            RosterAttendance.objects.update_or_create(
                roster=instance.session.roster,
                session=instance.session,
                person=instance.person,
                defaults={
                    'status': status,
                    'marked_at': instance.recognized_at
                }
            )


@receiver(post_save, sender=RosterAttendance)
def create_absent_attendance_record(sender, instance, created, **kwargs):
    """Create absent attendance records for expected persons"""
    if created:
        session = instance.session
        person = instance.person
        
        # Check if person was already recognized
        recognition_exists = Recognition.objects.filter(
            session=session,
            person=person
        ).exists()

        if not recognition_exists:
            # Create/update AttendanceSummary for backward compatibility
            AttendanceSummary.objects.get_or_create(
                session=session,
                person=person,
                defaults={'status': 'absent'}
            )
            
            # Create/update RosterAttendance if session has a roster
            if session.roster:
                RosterAttendance.objects.get_or_create(
                    roster=session.roster,
                    session=session,
                    person=person,
                    defaults={'status': 'absent'}
                )


@receiver(post_delete, sender=Recognition)
def mark_as_absent_on_recognition_delete(sender, instance, **kwargs):
    """Mark as absent when recognition is deleted"""
    session = instance.session
    person = instance.person
    
    # Only process if session has a roster
    if not session.roster:
        return
    
    # Check if person is expected in this session's roster
    is_expected = session.roster.people.filter(id=person.id).exists()

    if is_expected:
        # Update RosterAttendance to mark as absent
        RosterAttendance.objects.update_or_create(
            roster=session.roster,
            session=session,
            person=person,
            defaults={'status': 'absent', 'marked_at': None}
        )
        
        # Update AttendanceSummary for backward compatibility
        AttendanceSummary.objects.update_or_create(
            session=session,
            person=person,
            defaults={'status': 'absent', 'marked_at': None}
        )
    else:
        # If not expected, delete the attendance records
        RosterAttendance.objects.filter(
            roster=session.roster,
            session=session,
            person=person
        ).delete()
        
        AttendanceSummary.objects.filter(
            session=session,
            person=person
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
