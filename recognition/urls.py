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
    path('detect/', views.face_detection_page, name='face_detection'),
    path('live/', views.live_recognition_page, name='live_face_page'),
    path('live_feed/', views.live_face_recognition_stream, name='live_face_stream'),
]