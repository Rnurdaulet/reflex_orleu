from django.db import models

from apps.people.models import Person


class QuizQuestion(models.Model):
    external_id = models.CharField("ID", max_length=100, unique=True)
    name_ru = models.TextField("Вопрос (рус)", blank=False)
    name_kk = models.TextField("Сұрақ (қаз)", blank=False)
    name_en = models.TextField("Question (eng)", blank=False, default='q')

    def __str__(self):
        return f"[{self.external_id}] {self.name_ru[:50]}"


class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="answers")
    external_id = models.CharField("ID", max_length=100)
    name_ru = models.CharField("Ответ (рус)", max_length=255)
    name_kk = models.CharField("Жауап (қаз)", max_length=255)
    name_en = models.CharField("Answer (eng)", max_length=255, default='q')
    is_correct = models.BooleanField("Правильный ответ", default=False)

    def __str__(self):
        return f"{self.external_id} {self.name_ru}"


class QuizSession(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"Session for {self.person} on {self.started_at.strftime('%Y-%m-%d')}"


class QuizResponse(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    answer = models.ForeignKey(QuizAnswer, on_delete=models.SET_NULL, null=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question.external_id} → {self.answer.external_id if self.answer else 'None'}"


from django.utils.timezone import now, timedelta


class QuizConfig(models.Model):
    title = models.CharField(max_length=255, default="Main Quiz")
    start_time = models.DateTimeField("Начало теста")
    duration_minutes = models.PositiveIntegerField("Продолжительность (в минутах)", default=90)
    test_duration_minutes = models.PositiveIntegerField(
        "Время на сам тест (мин)", default=30,
        help_text="Сколько минут даётся на тест после нажатия «Начать»")
    from datetime import timedelta

    def end_time(self):
        if self.start_time is not None:
            return self.start_time + timedelta(minutes=self.duration_minutes)
        return None

    def is_active(self):
        now_time = now()
        return self.start_time <= now_time <= self.end_time()

    def display_end_time(self):
        et = self.end_time()
        return et.strftime('%d.%m.%Y %H:%M') if et else "—"

    display_end_time.short_description = "Окончание теста"

    def __str__(self):
        start = self.start_time.strftime('%d.%m.%Y %H:%M') if self.start_time else "???"
        return f"{self.title} — {start} ({self.duration_minutes} мин)"


class Scenario(models.Model):
    external_id = models.CharField("ID", max_length=100, unique=True)
    name_ru = models.TextField("Название (RU)")
    name_kk = models.TextField("Атау (KK)")
    name_en = models.TextField("Name (EN)")

    situation_ru = models.TextField("Ситуация (RU)")
    situation_kk = models.TextField("Жағдай (KK)")
    situation_en = models.TextField("Situation (EN)")

    sp_ru = models.TextField("SP (RU)", blank=True)
    sp_kk = models.TextField("SP (KK)", blank=True)
    sp_en = models.TextField("SP (EN)", blank=True)

    questions = models.ManyToManyField(
        QuizQuestion,
        verbose_name="Вопросы",
        related_name="scenarios",
        blank=True
    )

    class Meta:
        verbose_name = "Сценарий"
        verbose_name_plural = "Сценарии"

    def __str__(self):
        return f"[{self.external_id}] {self.name_ru[:50]}"
