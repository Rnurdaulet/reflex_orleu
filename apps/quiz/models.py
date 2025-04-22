from django.db import models

class QuizQuestion(models.Model):
    external_id = models.CharField("ID", max_length=100, unique=True)
    name_ru = models.TextField("Вопрос (рус)", blank=False)
    name_kk = models.TextField("Сұрақ (қаз)", blank=False)

    def __str__(self):
        return f"[{self.external_id}] {self.name_ru[:50]}"

class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="answers")
    external_id = models.CharField("ID", max_length=100, unique=True)
    name_ru = models.CharField("Ответ (рус)", max_length=255)
    name_kk = models.CharField("Жауап (қаз)", max_length=255)
    is_correct = models.BooleanField("Правильный ответ", default=False)

    def __str__(self):
        return f"{self.external_id} {self.name_ru} )"
