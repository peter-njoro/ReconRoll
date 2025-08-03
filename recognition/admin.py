from django.contrib import admin
from .models import Session, Event, Student, AttendanceRecord, FaceEncoding
# Register your models here.

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'created_by', 'start_time', 'status')
    search_fields = ('subject', )
    list_filter = ('status', )

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'session', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('message',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'registration_number', 'email', 'course', 'year_of_study')
    search_fields = ('full_name', 'registration_number', 'email')
    list_filter = ('course', 'year_of_study')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'timestamp', 'source', 'is_late')
    list_filter = ('source', 'is_late')
    search_fields = ('student__full_name', 'session__subject')
    
@admin.register(FaceEncoding)
class FaceEncodingAdmin(admin.ModelAdmin):
    list_display = ('student', 'file_path', 'created_at')
    search_fields = ('student__full_name',)