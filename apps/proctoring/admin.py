from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import VideoChunk

@admin.register(VideoChunk)
class VideoChunkAdmin(ModelAdmin):  # 🧩 используем unfold ModelAdmin
    list_display = ('id', 'user', 'chunk_index', 'created_at', 's3_link')
    list_filter = ('user',)
    search_fields = ('user__username', 's3_key')

    fieldsets = (
        ('Информация о чанке', {
            'fields': ('user', 'chunk_index', 'created_at', 's3_key')
        }),
    )

    def s3_link(self, obj):
        url = f"https://storage.yandexcloud.net/{obj.s3_key}"
        return f'<a href="{url}" target="_blank">🎥 Открыть</a>'
    s3_link.allow_tags = True
    s3_link.short_description = 'Просмотр'