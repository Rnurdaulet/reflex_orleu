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
