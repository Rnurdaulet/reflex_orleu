from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Person
from apps.survey.models import SurveyResponse

class SurveySubmittedFilter(admin.SimpleListFilter):
    title = "Анкета"
    parameter_name = "survey_submitted"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Сдана"),
            ("no", "Не сдана"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(surveyresponse__is_submitted=True)
        if self.value() == "no":
            return queryset.exclude(surveyresponse__is_submitted=True)
        return queryset


@admin.register(Person)
class PersonAdmin(ModelAdmin):
    list_display = ("full_name", "iin", "external_id", "user", "has_submitted_survey")
    search_fields = ("full_name", "iin")
    list_filter = (SurveySubmittedFilter,)

    @admin.display(boolean=True, description="Submitted")
    def has_submitted_survey(self, obj):
        return hasattr(obj, "surveyresponse") and obj.surveyresponse.is_submitted


from .models import EducationLevel, Region, Person, QuizPerson


@admin.register(EducationLevel)
class EducationLevelAdmin(ModelAdmin):
    list_display = ("external_id", "description")
    search_fields = ("external_id", "description")
    ordering = ("external_id",)


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ("external_id", "description")
    search_fields = ("external_id", "description")
    ordering = ("external_id",)

@admin.register(QuizPerson)
class QuizPersonAdmin(ModelAdmin):
    list_display = (
        "external_id",
        "person",
        "firstname",
        "lastname",
        "gender",
        "age",
        "years_experience",
        "teaching_experience",
        "education",
        "region",
        "language",
    )
    search_fields = ("external_id", "firstname", "lastname", "person__iin", "person__full_name")
    list_filter = ("gender", "education", "region")
    readonly_fields = ("external_id","signature_data","signature")
    autocomplete_fields = ("person", "education", "region")