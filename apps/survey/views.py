from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from utils.pdf_utils import generate_survey_pdf
from .models import Person, SurveyResponse
import base64, json, requests


from django.shortcuts import render
from django.http import FileResponse, HttpResponse
from .models import SurveyResponse
import os, zipfile
from io import BytesIO

def build_preview_text(survey):
    return json.dumps({
        "external_id": survey.external_id,
        "full_name": survey.full_name,
        "gender": survey.gender,
        "age": survey.age,
        "answer_1": survey.answer_1,
        "answer_2": survey.answer_2,
        "answer_3": survey.answer_3,
        "answer_4": survey.answer_4,
        "answer_5": survey.answer_5,
    }, ensure_ascii=False, indent=2)

@login_required
def survey_page(request):
    person = Person.objects.filter(user=request.user).first()
    if not person:
        return render(request, "survey/no_person.html")

    if hasattr(person, "surveyresponse") and person.surveyresponse.is_submitted:
        return render(request, "survey/already_submitted.html", {
            "survey": person.surveyresponse  # 👈 важно!
        })

    return render(request, "survey/form.html", {"person": person})

@login_required
def submit_survey_draft(request):
    if request.method != "POST":
        return redirect("survey_page")

    person = Person.objects.get(user=request.user)
    data = request.POST

    survey, _ = SurveyResponse.objects.update_or_create(
        person=person,
        defaults={
            "external_id": data.get("external_id"),
            "full_name": data.get("full_name"),
            "gender": data.get("gender"),
            "age": data.get("age"),
            "answer_1": data.get("answer_1"),
            "answer_2": data.get("answer_2"),
            "answer_3": data.get("answer_3"),
            "answer_4": data.get("answer_4"),
            "answer_5": data.get("answer_5"),
            "is_submitted": False
        }
    )
    return redirect("survey_preview")

@login_required
def survey_preview(request):
    person = Person.objects.get(user=request.user)
    survey = person.surveyresponse
    preview_json = build_preview_text(survey)
    return render(request, "survey/preview.html", {
        "survey": survey,
        "preview_json": preview_json
    })

@csrf_exempt
@login_required
def finalize_signed_survey(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Метод не поддерживается"}, status=405)

    try:
        signed_data = request.POST.get("signature")
        person = Person.objects.get(user=request.user)
        survey = person.surveyresponse

        preview_text = build_preview_text(survey)
        original_data = base64.b64encode(preview_text.encode("utf-8")).decode("utf-8")

        print("PREVIEW TEXT (backend):")
        print(preview_text)
        proxies = {
            "http": "http://sslvpn-proxy:3128",
            "https": "http://sslvpn-proxy:3128"
        }
        response = requests.post("http://192.168.28.12:14579/cms/verify", json={
            "cms": signed_data,
            "revocationCheck": ["OCSP"],
            "data": original_data,
            "detached": True
        }, timeout=30,proxies=proxies)

        response.raise_for_status()
        result = response.json()

        if not result.get("valid"):
            return JsonResponse({"success": False, "message": "Подпись не прошла проверку"})

        survey.signature = signed_data
        survey.is_submitted = True
        generate_survey_pdf(survey)
        survey.save()

        return JsonResponse({"success": True, "message": "Успешно отправлено"})

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

@staff_member_required
@login_required
def survey_list_view(request):
    surveys = SurveyResponse.objects.filter(is_submitted=True)
    return render(request, "survey/list.html", {"surveys": surveys})

@login_required
def download_all_surveys_pdf(request):
    buffer = BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED)

    surveys = SurveyResponse.objects.filter(is_submitted=True, pdf_file__isnull=False)

    for survey in surveys:
        if survey.pdf_file and os.path.exists(survey.pdf_file.path):
            zip_file.write(survey.pdf_file.path, arcname=os.path.basename(survey.pdf_file.name))

    zip_file.close()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename="all_surveys.zip")