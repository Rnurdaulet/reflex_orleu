from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import VideoChunk, QuizLog


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


@admin.register(QuizLog)
class QuizLogAdmin(ModelAdmin):
    list_display = ('id', 'user_link', 'event', 'short_detail', 'chunk_index', 'timestamp', 'created_at')
    list_filter = ('event', 'created_at')
    search_fields = ('user__username', 'event', 'detail', 'session_id')
    ordering = ('-timestamp',)

    fieldsets = (
        ('Информация о логе', {
            'fields': ('user', 'session_id', 'event', 'detail', 'video_chunk', 'timestamp', 'created_at'),
            'classes': ('wide',),
        }),
    )

    readonly_fields = ('user', 'session_id', 'event', 'detail', 'timestamp', 'created_at', 'video_chunk')

    def user_link(self, obj):
        if obj.user:
            return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
        return "-"
    user_link.short_description = 'Пользователь'

    def short_detail(self, obj):
        if obj.detail:
            return (obj.detail[:50] + '...') if len(obj.detail) > 50 else obj.detail
        return "-"
    short_detail.short_description = 'Описание события'

    def chunk_index(self, obj):
        if obj.video_chunk:
            return obj.video_chunk.chunk_index
        return "-"
    chunk_index.short_description = 'Чанк №'