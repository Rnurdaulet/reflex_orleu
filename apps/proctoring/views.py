# views.py

import time
import boto3
from django.http import JsonResponse
from django.utils.html import format_html
from django.views.decorators.csrf import csrf_exempt
from .models import VideoChunk

# можно обернуть в @login_required
@csrf_exempt
def get_presigned_url(request):
    user = request.user if request.user.is_authenticated else None

    chunk_index = int(request.GET.get('index', 0))
    timestamp = int(time.time())
    key = f"recordings/{user.id if user else 'anonymous'}/chunk_{timestamp}_{chunk_index}.webm"

    s3 = boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        aws_access_key_id='YCAJEcFxPkU3rSNvhKybvO65C',
        aws_secret_access_key='YCMyiUMfaDbPog1OHu-SUTLMyUcajXEpxGkC2_uP'
    )

    presigned_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': 'rrvideos',
            'Key': key,
            'ContentType': 'video/webm',
        },
        ExpiresIn=600,
    )

    VideoChunk.objects.create(
        user=user,
        s3_key=key,
        chunk_index=chunk_index
    )

    return JsonResponse({
        'url': presigned_url,
        'key': key
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import VideoChunk

@login_required
def playback_view(request):
    chunks = VideoChunk.objects.filter(user=request.user).order_by("chunk_index")

    playlist = [
        f"https://storage.yandexcloud.net/rrvideos/{chunk.s3_key}"
        for chunk in chunks
    ]

    return render(request, "proctoring/playback.html", {"playlist": playlist})

from livekit import api
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def livekit_token_view(request):
    user = request.user
    room_name = request.GET.get("room", "default-room")

    # Безопасное получение identity
    if user.username and user.username.strip():
        user_identity = user.username.strip()
    elif user.id:
        user_identity = f"user_{user.id}"
    else:
        return JsonResponse({"error": "Cannot determine user identity"}, status=400)

    # Генерация токена через livekit.api
    token = (
        api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
        )
        .with_identity(user_identity)                  # уникальный identity
        .with_name(user.username or user_identity) # имя (если есть)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )

    jwt_token = token.to_jwt()

    return JsonResponse({"token": jwt_token})

