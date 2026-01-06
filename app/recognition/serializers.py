from rest_framework import serializers
from .models import Session, Student, AttendanceRecord, Event

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'full_name', 'student_id', 'class_group']

class SessionSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    recognition = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Session
        fields = ['id', 'subject', 'class_group', 'status', 'created_by', 'created_at', 'start_time', 'end_time', 'notes', 'recognition']
        read_only_fields = ['id', 'created_by', 'created_at', 'start_time', 'recognition', 'status', 'end_time']

    def get_recognition(self, obj):
        from django.utils import timezone
        from .recognition_runner import active_recognition
        
        active_data = active_recognition.get(str(obj.id), {})
        is_running = active_data.get("thread") and active_data["thread"].is_alive()
        
        present_count = AttendanceRecord.objects.filter(session=obj).count()
        expected_count = obj.class_group.students.count() if obj.class_group else 0
        attendance_percentage = round((present_count / expected_count * 100), 2) if expected_count > 0 else 0
        
        return {
            'is_running': bool(is_running),
            'mode': active_data.get('mode', 'none'),
            'present_count': present_count,
            'expected_count': expected_count,
            'attendance_percentage': attendance_percentage
        }
    
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_type', 'message', 'timestamp', 'severity']

