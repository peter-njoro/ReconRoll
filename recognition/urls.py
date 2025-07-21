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
]