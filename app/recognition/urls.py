"""Defines url patterns for the recognition app."""

from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('', views.index, name='index'),
    path('enroll/', views.enroll_view, name='enroll'),
    path('enroll/progress/', views.enroll_progress, name='enroll_progress'),
    path('enroll/success', views.enroll_success, name='enroll_success'),

    # Session creation and management
    path('session/create/', views.start_session_view, name='start_session_view'),
    path('session/<uuid:session_id>/start/', views.start_session_view, name='start_session'),
    path('session/<uuid:session_id>/end/', views.end_session_view, name='end_session'),
    path('session/<uuid:session_id>/', views.session_detail, name='session_detail'),

    # Session list
    path('sessions/', views.sessions_list, name='sessions_list'),
    
    path('session/<uuid:session_id>/status/', views.session_status_api, name='session_status'),
    path('session/<uuid:session_id>/start_recognition/', views.start_recognition_view, name='start_recognition'),

    # API endpoints
    path('session/<uuid:session_id>/status/', views.session_status_api, name='session_status'),
    
    # Partial views for AJAX updates
    path('session/<uuid:session_id>/events_partial/', views.session_events_partial, name='session_events_partial'),
    path('session/<uuid:session_id>/present_partial/', views.session_present_students_partial, name='session_present_partial'),
    path('session/<uuid:session_id>/absent_partial/', views.session_absent_students_partial, name='session_absent_partial'),
    path('session/<uuid:session_id>/unidentified_partial/', views.session_unidentified_faces_partial, name='session_unidentified_partial'),
    path('session/<uuid:session_id>/progress_partial/', views.recognition_progress_partial, name='recognition_progress_partial'),
]
