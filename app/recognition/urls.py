"""Defines url patterns for the recognition app."""

from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('info/', views.index, name='index'),
    path('enroll/', views.enroll_view, name='enroll'),
    path('enroll/progress/', views.enroll_progress, name='enroll_progress'),
    path('enroll/success', views.enroll_success, name='enroll_success'),
    
    # Session creation
    path('session/create/', views.create_session_view, name='create_session_view'),
    
    # Session management
    path('sessions/', views.sessions_list, name='sessions_list'),
    path('session/<uuid:session_id>/', views.session_detail, name='session_detail'),
    path('session/<uuid:session_id>/stop/', views.end_session_view, name='end_session'),
    path('session/<uuid:session_id>/stop-all/', views.stop_all_sessions_view, name='stop_all_sessions'),
    path('session/<uuid:session_id>/update/', views.update_session_view, name='update_session'),
    
    # API endpoints
    
    # Partial views
    path('session/<uuid:session_id>/events_partial/', views.session_events_partial, name='session_events_partial'),
    path('session/<uuid:session_id>/present_partial/', views.session_present_students_partial, name='session_present_partial'),
    path('session/<uuid:session_id>/absent_partial/', views.session_absent_students_partial, name='session_absent_partial'),
    path('session/<uuid:session_id>/unidentified_partial/', views.session_unidentified_faces_partial, name='session_unidentified_partial'),
    path('session/<uuid:session_id>/progress_partial/', views.recognition_progress_partial, name='recognition_progress_partial'),

    # frame fowarding for windows
    path("session/<uuid:session_id>/upload_frame/", views.upload_frame, name="upload_frame"),
]