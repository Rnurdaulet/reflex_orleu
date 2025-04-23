from django.urls import path
from . import views

urlpatterns = [
path("start/", views.quiz_start_view, name="quiz_start"),
    path("take/", views.quiz_take_view, name="quiz_take"),
    path("preview/", views.quiz_preview_view, name="quiz_preview"),
    path("preview/sign/", views.finalize_signed_quiz, name="quiz_sign"),
    path("submitted/", views.quiz_submitted_view, name="quiz_submitted"),
    path("closed/", views.quiz_closed_view, name="quiz_closed"),
    path("already-submitted/", views.quiz_already_submitted_view, name="quiz_already_submitted"),
    path("results/", views.quiz_results_view, name="quiz_results"),
    path("results/export/csv/", views.export_results_csv, name="export_quiz_csv"),
    path("results/export/excel/", views.export_results_excel, name="export_quiz_excel"),
]
