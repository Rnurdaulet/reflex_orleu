from django.urls import path
from .views import survey_page, submit_survey_response

urlpatterns = [
    path("survey/", survey_page, name="survey_page"),  # GET+POST форма
    path("survey/submit", submit_survey_response, name="survey_submit_api"),  # API POST only
]
