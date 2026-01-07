from rest_framework import serializers
from .models import Session, Student, AttendanceRecord, Event, ClassGroup


class StudentSerializer(serializers.ModelSerializer):
    class_groups = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'registration_number', 'email', 'course', 'year_of_study', 'class_groups']


class SessionSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    recognition = serializers.SerializerMethodField(read_only=True)
    # Accept class group by name on create/update from frontend
    class_group_name = serializers.CharField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Session
        fields = ['id', 'subject', 'class_group', 'class_group_name', 'status', 'created_by', 'created_at', 'start_time', 'end_time', 'notes', 'recognition']
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

    def create(self, validated_data):
        # Handle optional class_group_name coming from frontend
        class_group_name = validated_data.pop('class_group_name', None)
        class_group_obj = None
        if class_group_name:
            class_group_obj, _ = ClassGroup.objects.get_or_create(name=class_group_name)

        session = super().create(validated_data)
        if class_group_obj:
            session.class_group = class_group_obj
            session.save()
        return session

    def update(self, instance, validated_data):
        # allow updating via class_group_name as well
        class_group_name = validated_data.pop('class_group_name', None)
        if class_group_name is not None:
            class_group_obj, _ = ClassGroup.objects.get_or_create(name=class_group_name)
            instance.class_group = class_group_obj
        return super().update(instance, validated_data)
    
    def validate_class_group_name(self, value):
        # Reject empty or whitespace-only names
        if value is None:
            return value
        if isinstance(value, str) and value.strip() == '':
            raise serializers.ValidationError('class_group_name may not be empty.')
        return value.strip() if isinstance(value, str) else value
    
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_type', 'message', 'timestamp', 'severity']


class ClassGroupSerializer(serializers.ModelSerializer):
    students = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), many=True, required=False)

    class Meta:
        model = ClassGroup
        fields = ['id', 'name', 'description', 'students', 'created_at']

