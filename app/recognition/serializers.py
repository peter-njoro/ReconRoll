from rest_framework import serializers
from .models import Session, Student, AttendanceRecord, Event

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'full_name', 'student_id', 'class_group']

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'subject', 'class_group', 'status', 'end_time']

        def get_present_count(self, obj):
            return obj.attendance_records.count()
        def get_expected_count(self, obj):
            return obj.class_group.students.count() if obj.class_group else 0
    
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_type', 'message', 'timestamp', 'severity']

