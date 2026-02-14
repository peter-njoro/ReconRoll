from django.contrib import admin
from .models import (
    Person, FaceEncoding, Session,
    SessionExpectedPerson, Recognition, AttendanceSummary
)
from users.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_verified', 'created_at']
    list_filter = ['is_active', 'is_verified', 'is_staff', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Person)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'identification_number', 'email', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['first_name', 'last_name', 'identification_number', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['last_name', 'first_name']

    def get_full_name(self, obj):
        return obj.get_full_name()

    get_full_name.short_description = 'Full Name'

@admin.register(FaceEncoding)
class FaceEncodingAdmin(admin.ModelAdmin):
    list_display = ['person', 'is_primary', 'quality_score', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['person__first_name', 'person__last_name', 'person__identification_number']
    readonly_fields = ['created_at', 'updated_at', 'image_hash']
    ordering = ['-created_at']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'session_type', 'start_time', 'status', 'expected_count', 'created_by']
    list_filter = ['status', 'session_type', 'start_time']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-start_time']
    date_hierarchy = 'start_time'


@admin.register(SessionExpectedPerson)
class SessionExpectedPersonAdmin(admin.ModelAdmin):
    list_display = ['session', 'person', 'created_at']
    list_filter = ['created_at']
    search_fields = ['session__name', 'person__first_name', 'person__last_name', 'person__identification_number']
    ordering = ['-created_at']


@admin.register(Recognition)
class RecognitionAdmin(admin.ModelAdmin):
    list_display = ['person', 'session', 'recognized_at', 'confidence_score', 'is_verified']
    list_filter = ['is_verified', 'recognized_at']
    search_fields = ['person__first_name', 'person__last_name', 'session__name']
    readonly_fields = ['recognized_at']
    ordering = ['-recognized_at']
    date_hierarchy = 'recognized_at'


@admin.register(AttendanceSummary)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['person', 'session', 'status', 'marked_at', 'updated_at']
    list_filter = ['status', 'marked_at', 'updated_at']
    search_fields = ['person__first_name', 'person__last_name', 'session__name']
    readonly_fields = ['updated_at']
    ordering = ['-marked_at']