# models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class VideoChunk(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    s3_key = models.CharField(max_length=512)
    chunk_index = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk {self.chunk_index} by {self.user.username}"

# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# models.py
class QuizLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quiz_logs",
        verbose_name="Пользователь"
    )
    session_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="ID сессии"
    )
    event = models.CharField(
        max_length=255,
        verbose_name="Тип события"
    )
    detail = models.TextField(
        null=True,
        blank=True,
        verbose_name="Подробности"
    )
    timestamp = models.DateTimeField(
        verbose_name="Время события на клиенте"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано в БД"
    )
    video_chunk = models.ForeignKey(
        'VideoChunk',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="Связанный чанк видео"
    )

    class Meta:
        verbose_name = "Лог теста"
        verbose_name_plural = "Логи тестов"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['video_chunk']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.event} @ {self.timestamp}"


