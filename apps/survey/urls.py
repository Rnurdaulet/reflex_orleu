from django.urls import path
from .views import (
    survey_page, submit_survey_draft,
    survey_preview, finalize_signed_survey
)

urlpatterns = [
    path("survey/", survey_page, name="survey_page"),  # форма
    path("survey/submit", submit_survey_draft, name="survey_submit"),
    path("survey/preview", survey_preview, name="survey_preview"),
    path("survey/sign", finalize_signed_survey, name="survey_sign"),
]
