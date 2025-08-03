"""Defines url patterns for the recognition app."""

from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('', views.index, name='index'),
    path('enroll/', views.enroll_view, name='enroll'),
    path('enroll/success', views.enroll_success, name='enroll_success'),
    path('session/start/', views.start_session_view, name='start_session'),
    path('session/<uuid:session_id>/', views.session_detail, name='session_detail'),
    path('session/<uuid:session_id>/start_recognition/', views.start_recognition_view, name='start_recognition'),
    path('session/<uuid:session_id>/end/', views.end_session_view, name='end_session'),
    path('session/<uuid:session_id>/events_partial/', views.session_events_partial, name='session_events_partial'),
    path('session/<uuid:session_id>/present_partial/', views.session_present_students_partial, name='session_present_partial'),
    path('session/<uuid:session_id>/absent_partial/', views.session_absent_students_partial, name='session_absent_partial'),
    path('session/<uuid:session_id>/unidentified_partial/', views.session_unidentified_faces_partial, name='session_unidentified_partial'),
    path('session/<uuid:session_id>/progress_partial/', views.recognition_progress_partial, name='recognition_progress_partial')
]