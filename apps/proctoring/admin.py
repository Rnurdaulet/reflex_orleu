from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import VideoChunk


@admin.register(VideoChunk)
class VideoChunkAdmin(ModelAdmin):
    list_display = ('id', 'user', 'chunk_index', 'created_at', 's3_link')
    list_filter = ('user', 'created_at')
    search_fields = ('user__username', 's3_key')
    ordering = ('-created_at',)

    fieldsets = (
        ('Чанк видео', {
            'fields': ('user', 'chunk_index', 's3_key', 'created_at'),
            'classes': ('wide',),
        }),
    )

    readonly_fields = ('created_at',)

    def s3_link(self, obj):
        url = f"https://storage.yandexcloud.net/rrvideos/{obj.s3_key}"
        return format_html('<a href="{}" target="_blank">🎥 Открыть</a>', url)

    s3_link.short_description = 'Просмотр в S3'
