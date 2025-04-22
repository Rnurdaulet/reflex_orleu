from django.contrib.auth.models import User
from django.db import models

class EducationLevel(models.Model):
    external_id = models.PositiveIntegerField(unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.external_id} - {self.description}'

class Region(models.Model):
    external_id = models.PositiveIntegerField(unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.external_id} - {self.description}'


class Person(models.Model):
    iin = models.CharField("ИИН", max_length=12, unique=True)
    full_name = models.CharField("ФИО", max_length=255)
    external_id = models.CharField("Внешний ID", max_length=100)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    signature = models.TextField("Подпись", blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.iin})"


class QuizPerson(models.Model):
    GENDER_CHOICES = (
        ("male", "Мужской"),
        ("female", "Женский"),
    )
    person = models.OneToOneField(Person, on_delete=models.CASCADE, verbose_name="Пользователь")
    external_id = models.CharField("Внешний ID", max_length=100)
    firstname = models.CharField("firstname", max_length=255)
    lastname = models.CharField("lastname", max_length=255)
    gender = models.CharField("Пол", max_length=6, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField("Возраст")
    years_experience = models.PositiveIntegerField()
    education = models.ForeignKey(EducationLevel, on_delete=models.PROTECT, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, null=True, blank=True)
    signature_data = models.TextField("Подпись Данные по тесту", blank=True, null=True)
    signature = models.TextField("Подпись", blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.person:
            self.external_id = self.person.external_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.external_id} ({self.firstname} {self.lastname})"