from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Person, SurveyResponse

@login_required
def survey_page(request):
    person = Person.objects.filter(user=request.user).first()
    if not person:
        return render(request, "survey/no_person.html")

    if hasattr(person, "surveyresponse"):
        return render(request, "survey/already_submitted.html", {"response": person.surveyresponse})

    return render(request, "survey/form.html", {"person": person})


import json
import base64
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Person, SurveyResponse

NCANODE_URL = "http://192.168.28.12:14579/cms/verify"

@csrf_exempt
def submit_survey_response(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Метод не поддерживается"}, status=405)

    try:
        signed_data = request.POST.get("signature")
        original_text = ""

        # Собираем оригинальные данные (тот же формат, что подписывался на фронте)
        for field in ["external_id", "full_name", "gender", "age", "answer_1", "answer_2", "answer_3", "answer_4", "answer_5"]:
            value = request.POST.get(field, "")
            original_text += f"{field}: {value}\n"

        original_data = base64.b64encode(original_text.encode("utf-8")).decode("utf-8")

        # Проверяем подпись через NCANode
        response = requests.post(NCANODE_URL, json={
            "cms": signed_data,
            "revocationCheck": ["OCSP"]
        }, timeout=5)
        response.raise_for_status()
        result = response.json()

        if not result.get("valid") or not result.get("signers"):
            return JsonResponse({"success": False, "message": "Подпись не прошла проверку"}, status=400)

        subject = result["signers"][0]["certificates"][0]["subject"]
        iin = subject.get("iin")
        full_name_cert = subject.get("commonName")

        if not iin:
            return JsonResponse({"success": False, "message": "ИИН не найден в сертификате"}, status=400)

        person = Person.objects.filter(iin=iin).first()
        if not person:
            return JsonResponse({"success": False, "message": "Пользователь не найден"}, status=404)

        if hasattr(person, "surveyresponse"):
            return JsonResponse({"success": False, "message": "Вы уже отправили анкету"}, status=409)

        SurveyResponse.objects.create(
            person=person,
            external_id=request.POST.get("external_id"),
            full_name=request.POST.get("full_name"),
            gender=request.POST.get("gender"),
            age=request.POST.get("age"),
            signature=signed_data,
            answer_1=request.POST.get("answer_1"),
            answer_2=request.POST.get("answer_2"),
            answer_3=request.POST.get("answer_3"),
            answer_4=request.POST.get("answer_4"),
            answer_5=request.POST.get("answer_5"),
        )

        return JsonResponse({"success": True, "message": "Ответ принят. Спасибо!"})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"Ошибка: {str(e)}"}, status=500)
