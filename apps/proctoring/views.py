# views.py

import time
import boto3
from django.http import JsonResponse
from django.utils.html import format_html
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .models import VideoChunk
from ..people.models import Person, QuizPerson


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


def livekit_token_view(request):
    user = request.user
    room_name = request.GET.get("room", "default-room")
    identity = request.GET.get('identity')
    if not identity:
        try:
            person = Person.objects.get(user=user)
            identity = person.external_id.strip()
            if not identity:
                return JsonResponse({"error": "External ID is empty"}, status=400)
        except Person.DoesNotExist:
            return JsonResponse({"error": "Cannot determine external_id for user"}, status=400)

    # Генерация токена через livekit.api
    token = (
        api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
        )
        .with_identity(identity)                  # уникальный identity
        .with_name(identity) # имя (если есть)
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



# views.py
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.http import JsonResponse
from .models import QuizLog

@csrf_exempt
@login_required
def upload_logs(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        logs = data.get('logs', [])

        if not isinstance(logs, list):
            return JsonResponse({"error": "Invalid logs format"}, status=400)

        created = 0

        for entry in logs:
            if not isinstance(entry, dict):
                continue  # пропускаем неправильные записи

            chunk_index = entry.get('chunk_index')
            video_chunk = None

            if chunk_index is not None:
                video_chunk = VideoChunk.objects.filter(
                    user=request.user,
                    chunk_index=chunk_index
                ).first()

            QuizLog.objects.create(
                user=request.user,
                session_id=entry.get('session_id') or None,
                event=entry.get('event') or '',
                detail=entry.get('detail', ''),
                timestamp=entry.get('timestamp') or now(),
                video_chunk=video_chunk,
            )

            created += 1

        return JsonResponse({"status": "ok", "created": created})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
def moderator_room_view(request):
    persons = Person.objects.all().order_by('full_name')
    return render(request, 'proctoring/moderator_room.html', {'persons': persons})

def get_person_identities(request):
    persons = Person.objects.exclude(external_id__isnull=True).exclude(external_id='').values_list('external_id', flat=True)
    return JsonResponse({"identities": list(persons)})

@require_GET
def get_logs_by_external_id(request):
    external_id = request.GET.get('external_id')
    if not external_id:
        return JsonResponse({"error": "Не передан параметр external_id"}, status=400)

    try:
        person = Person.objects.get(external_id=external_id)
    except Person.DoesNotExist:
        return JsonResponse({"error": "Пользователь с таким external_id не найден"}, status=404)

    if not person.user:
        return JsonResponse({"error": "Пользователь не связан с User"}, status=400)

    logs = QuizLog.objects.filter(user=person.user).order_by('-timestamp')

    result = []
    for log in logs:
        s3_url = None
        if log.video_chunk:
            s3_url = f"https://storage.yandexcloud.net/rrvideos/{log.video_chunk.s3_key}"

        result.append({
            "id": log.id,
            "event": log.event,
            "detail": log.detail,
            "timestamp": log.timestamp,
            "created_at": log.created_at,
            "session_id": log.session_id,
            "video_chunk_id": log.video_chunk_id,
            "video_chunk_url": s3_url,
        })

    return JsonResponse({"logs": result})


def get_signed_users(request):
    signed_quiz_persons = QuizPerson.objects.filter(signature__isnull=False).exclude(signature="")

    result = []
    for person in signed_quiz_persons:
        result.append({
            "external_id": person.external_id,
            "full_name": f"{person.firstname} {person.lastname}",
            "signature_data": person.signature_data,
        })

    return JsonResponse({"signed_users": result})