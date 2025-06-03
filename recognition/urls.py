"""Defines url patterns for the recognition app."""

from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('', views.index, name='index'),
    path('enroll/', views.enroll_view, name='enroll'),
    path('enroll/success', views.enroll_success, name='enroll_success'),
    path('detect/', views.face_detection_page, name='face_detection'),
    path('video_feed/', views.face_detection_stream, name='video_feed'),
]