from django.contrib.auth.models import User
from django.db import models

class Person(models.Model):
    iin = models.CharField("ИИН", max_length=12, unique=True)
    full_name = models.CharField("ФИО", max_length=255)
    external_id = models.CharField("Внешний ID", max_length=100)
    signature = models.TextField("Подпись", blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.iin})"
