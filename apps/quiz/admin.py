from django.contrib import admin
from django.db import models
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    QuizConfig,
    QuizQuestion,
    QuizAnswer,
    QuizSession,
    QuizResponse, Scenario
)


# Inline для ответов внутри вопроса
class QuizAnswerInline(TabularInline):
    model = QuizAnswer
    extra = 2
    fields = ("external_id", "name_ru", "name_kk", "name_en", "is_correct")
    show_change_link = True


@admin.register(QuizQuestion)
class QuizQuestionAdmin(ModelAdmin):
    list_display = ("external_id", "name_ru", "name_kk", "name_en")
    search_fields = ("external_id", "name_ru", "name_kk", "name_en")
    inlines = [QuizAnswerInline]


@admin.register(QuizAnswer)
class QuizAnswerAdmin(ModelAdmin):
    list_display = ("external_id", "question", "name_ru", "is_correct")
    list_filter = ("question", "is_correct")
    search_fields = ("external_id", "name_ru", "name_kk", "name_en")
    autocomplete_fields = ("question",)


@admin.register(QuizSession)
class QuizSessionAdmin(ModelAdmin):
    list_display = ("person", "started_at", "submitted_at", "is_submitted")
    list_filter = ("is_submitted", "started_at")
    search_fields = ("person__full_name", "person__iin")


@admin.register(QuizResponse)
class QuizResponseAdmin(ModelAdmin):
    list_display = ("session", "question", "answer", "is_correct")
    list_filter = ("is_correct", "question")
    search_fields = ("question__name_ru", "answer__name_ru")
    autocomplete_fields = ("session", "question", "answer")


@admin.register(QuizConfig)
class QuizConfigAdmin(ModelAdmin):
    list_display = ("title", "start_time", "duration_minutes", "display_end_time", "is_active")
    readonly_fields = ("display_end_time",)
    search_fields = ("title",)


@admin.register(Scenario)
class ScenarioAdmin(ModelAdmin):
    list_display = ("external_id", "name_ru")
    filter_horizontal = ("questions",)
    # formfield_overrides = {
    #     models.TextField: {
    #         "widget": WysiwygWidget,
    #     }
    # }