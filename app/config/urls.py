"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from recognition.api import SessionViewSet, StudentViewSet, ClassGroupViewSet

router = DefaultRouter()
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'class-groups', ClassGroupViewSet, basename='classgroup')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('', include(router.urls)),
        path('', include('recognition.urls')),
        path('', include('users.urls')),
    ])),
    path('api/csrf/', ensure_csrf_cookie(lambda request: JsonResponse({'csrfToken': get_token(request)}))),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)