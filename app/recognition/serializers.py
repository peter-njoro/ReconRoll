from rest_framework import serializers
from .models import Session, Person, AttendanceSummary, Event, RosterAttendance


class PersonSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Person
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'identification_number',
            'email',
            'phone',
            'status',
            'date_of_birth',
            'notes',
            'created_at',
            'updated_at',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()


# Backwards compatibility
StudentSerializer = PersonSerializer


class SessionSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    recognition = serializers.SerializerMethodField(read_only=True)
    expected_people_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Session
        fields = [
            'id',
            'name',
            'description',
            'session_type',
            'start_time',
            'end_time',
            'expected_count',
            'expected_people_count',
            'status',
            'created_by',
            'created_at',
            'recognition',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_at',
            'recognition',
            'expected_people_count',
        ]

    def get_recognition(self, obj):
        from .recognition_runner import active_recognition
        
        active_data = active_recognition.get(str(obj.id), {})
        is_running = active_data.get("thread") and active_data["thread"].is_alive()
        
        present_count = AttendanceSummary.objects.filter(
            session=obj,
            status__in=['present', 'late']
        ).count()
        
        # Count expected people from roster if session has one
        if obj.roster:
            expected_count = RosterAttendance.objects.filter(roster=obj.roster, session=obj).count()
        else:
            expected_count = obj.expected_count or 0
        
        attendance_percentage = round((present_count / expected_count * 100), 2) if expected_count > 0 else 0
        
        return {
            'is_running': bool(is_running),
            'mode': active_data.get('mode', 'none'),
            'present_count': present_count,
            'expected_count': expected_count,
            'attendance_percentage': attendance_percentage
        }

    def get_expected_people_count(self, obj):
        # Count expected people from roster if session has one
        if obj.roster:
            return RosterAttendance.objects.filter(roster=obj.roster, session=obj).count()
        return obj.expected_count or 0
    
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_type', 'message', 'timestamp', 'severity']

