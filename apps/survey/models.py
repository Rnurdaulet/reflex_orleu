from django.db import models
from apps.people.models import Person


class SurveyResponse(models.Model):
    person = models.OneToOneField(Person, on_delete=models.CASCADE, verbose_name="Пользователь")
    external_id = models.CharField("Внешний ID", max_length=100, unique=True)
    full_name = models.CharField("Имя и фамилия", max_length=255)

    GENDER_CHOICES = (
        ("male", "Мужской"),
        ("female", "Женский"),
    )
    gender = models.CharField("Пол", max_length=6, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField("Возраст")
    submitted_at = models.DateTimeField("Дата заполнения", auto_now_add=True)
    signature = models.TextField("Подпись")

    # Ответы на вопросы
    answer_1 = models.TextField("Ответ на вопрос 1")
    answer_2 = models.TextField("Ответ на вопрос 2")
    answer_3 = models.TextField("Ответ на вопрос 3")
    answer_4 = models.TextField("Ответ на вопрос 4")
    answer_5 = models.TextField("Ответ на вопрос 5")

    def __str__(self):
        return f"{self.full_name} ({self.external_id})"
