# urls.py
from django.urls import path
from .views import get_presigned_url, playback_view, livekit_token_view, upload_logs

urlpatterns = [
    path('api/get-presigned-url/', get_presigned_url, name='get_presigned_url'),
    path('proctoring/playback/', playback_view, name='proctoring_playback'),
    path('api/livekit/token/', livekit_token_view, name='livekit_token'),

    path('api/upload-logs/', upload_logs, name='upload_logs')

]
