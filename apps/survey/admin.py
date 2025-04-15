from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SurveyResponse

@admin.register(SurveyResponse)
class SurveyResponseAdmin(ModelAdmin):
    list_display = ("full_name", "external_id", "gender", "age", "submitted_at")
    search_fields = ("full_name", "external_id")
    list_filter = ("gender", "submitted_at")
    readonly_fields = ("submitted_at",)
