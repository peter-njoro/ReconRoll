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
    path('session/create/', views.create_session_view, name='create_session'),
    
    # Session management
    path('sessions/', views.sessions_list, name='sessions_list'),
    path('sessions/stop-all/', views.stop_all_sessions_view, name='stop_all_sessions'),
    path('session/<uuid:session_id>/', views.session_detail, name='session_detail'),
<<<<<<< HEAD:app/recognition/urls.py
    path('session/<uuid:session_id>/end/', views.end_session_view, name='end_session'),
    path('sessions/stop-all/', views.stop_all_sessions, name='stop_all_sessions'),
    
    # API endpoints
    path('session/<uuid:session_id>/status/', views.session_status_api, name='session_status'),
    path('session/<uuid:session_id>/unidentified_faces_api/', views.session_unidentified_faces_api, name='session_unidentified_faces_api'),
    
    # Partial views
    path('session/<uuid:session_id>/events_partial/', views.session_events_partial, name='session_events_partial'),
    path('session/<uuid:session_id>/present_partial/', views.session_present_students_partial, name='session_present_students_partial'),
    path('session/<uuid:session_id>/absent_partial/', views.session_absent_students_partial, name='session_absent_students_partial'),
    path('session/<uuid:session_id>/unidentified_partial/', views.session_unidentified_faces_partial, name='session_unidentified_faces_partial'),
=======
    path('session/<uuid:session_id>/expected/', views.session_expected_people_view, name='session_expected_people'),
    path('session/<uuid:session_id>/start/', views.start_session_view, name='start_session'),
    path('session/<uuid:session_id>/stop/', views.end_session_view, name='end_session'),
    path('session/<uuid:session_id>/update/', views.update_session_view, name='update_session'),
    
    # API endpoints
    path('people/', views.get_people_with_encodings, name='get_people'),
    path('people/<uuid:person_id>/', views.get_person_detail, name='get_person_detail'),
    
    # Roster management
    path('rosters/', views.list_rosters, name='list_rosters'),
    path('roster/create/', views.create_roster, name='create_roster'),
    path('roster/<uuid:roster_id>/', views.get_roster_detail, name='get_roster_detail'),
    path('roster/<uuid:roster_id>/update/', views.update_roster, name='update_roster'),
    path('roster/<uuid:roster_id>/delete/', views.delete_roster, name='delete_roster'),
    
    # Partial views
    path('session/<uuid:session_id>/events_partial/', views.session_events_partial, name='session_events_partial'),
    path('session/<uuid:session_id>/present_partial/', views.session_present_people_partial, name='session_present_partial'),
    path('session/<uuid:session_id>/absent_partial/', views.session_absent_people_partial, name='session_absent_partial'),
    path('session/<uuid:session_id>/unidentified_partial/', views.session_unidentified_faces_partial, name='session_unidentified_partial'),
>>>>>>> main:backend/app/recognition/urls.py
    path('session/<uuid:session_id>/progress_partial/', views.recognition_progress_partial, name='recognition_progress_partial'),

    # NOTE: upload_frame is handled by DRF SessionViewSet in api.py
    # The DRF endpoint is: /api/sessions/<pk>/upload_frame/
]
