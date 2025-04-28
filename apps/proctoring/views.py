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
