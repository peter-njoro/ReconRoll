"""Defines url patterns for the recognition app."""

from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('', views.index, name='index'),
    path('enroll/', views.enroll_view, name='enroll'),
    path('enroll/success', views.enroll_success, name='enroll_success'),
    path('detect/', views.face_detection_page, name='face_detection'),
    path('live/', views.live_recognition_page, name='live_face_page'),
    path('live_feed/', views.live_face_recognition_stream, name='live_face_stream'),
]