# urls.py
from django.urls import path
from .views import get_presigned_url, playback_view

urlpatterns = [
    path('api/get-presigned-url/', get_presigned_url, name='get_presigned_url'),
    path('proctoring/playback/', playback_view, name='proctoring_playback'),
]
