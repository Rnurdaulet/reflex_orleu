# urls.py
from django.urls import path
from .views import get_presigned_url, playback_view, livekit_token_view, upload_logs, moderator_room_view, \
    get_person_identities, get_logs_by_external_id, get_signed_users, quiz_person_logs_view, quiz_person_list_view

urlpatterns = [
    path('api/get-presigned-url/', get_presigned_url, name='get_presigned_url'),
    path('proctoring/playback/', playback_view, name='proctoring_playback'),
    path('api/livekit/token/', livekit_token_view, name='livekit_token'),

    path('api/upload-logs/', upload_logs, name='upload_logs'),
    path('moderator/room/', moderator_room_view, name='moderator_room'),

    path('api/get-persons/', get_person_identities, name='get_persons'),
    path('api/logs/', get_logs_by_external_id, name='get_logs_by_external_id'),
    path('api/signed-users/', get_signed_users, name='get_signed_users'),
    path('quiz-persons/', quiz_person_list_view, name='quiz_person_list'),
    path('quiz-logs/<str:external_id>/', quiz_person_logs_view, name='quiz_person_logs'),

]
