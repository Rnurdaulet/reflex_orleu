from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import QuizQuestion, QuizAnswer

class QuizAnswerInline(TabularInline):
    model = QuizAnswer
    extra = 2


@admin.register(QuizQuestion)
class QuizQuestionAdmin(ModelAdmin):
    list_display = ("external_id", "name_ru")
    search_fields = ("external_id", "name_ru", "name_kk")
    inlines = [QuizAnswerInline]


@admin.register(QuizAnswer)
class QuizAnswerAdmin(ModelAdmin):
    list_display = ("question", "name_ru", "name_kk", "is_correct")
    list_filter = ("is_correct", "question")
    search_fields = ("name_ru", "name_kk")

