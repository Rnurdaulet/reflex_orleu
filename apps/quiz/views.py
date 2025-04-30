from datetime import timedelta
import csv, io, base64

from django.contrib.admin.views.decorators import staff_member_required
from openpyxl import Workbook
import requests
import json
import base64
import requests
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from apps.quiz.models import QuizConfig, QuizSession, QuizResponse, QuizQuestion, QuizAnswer, Scenario
from apps.people.models import Person, QuizPerson
from django.contrib.auth.decorators import login_required


@login_required
def quiz_start_view(request):
    config = QuizConfig.objects.first()
    # если окно ещё не открыто или уже закрыто
    if not config or not config.is_active():
        return redirect("quiz_closed")
    return render(request, "quiz/quiz_start.html", {
        "config": config
    })


@login_required
def quiz_take_view(request):
    person = request.user.person
    quiz_person = QuizPerson.objects.filter(person=person).first()
    config = QuizConfig.objects.first()

    # если тест закрыт
    if not config or not config.is_active():
        return redirect("quiz_closed")

    # если уже подписан — ничего редактировать нельзя
    if quiz_person and quiz_person.signature:
        return redirect("quiz_submitted")

    # получаем или создаём сессию
    session, created = QuizSession.objects.get_or_create(
        person=person,
        defaults={"is_submitted": False, "started_at": now()}
    )

    elapsed = now() - session.started_at
    if elapsed > timedelta(minutes=config.test_duration_minutes):
        return redirect("quiz_preview")  # вернём на предпросмотр

    # загружаем сценарии и вопросы
    scenarios = Scenario.objects.prefetch_related("questions__answers").all()

    # прогресс
    answered_ids = set(
        QuizResponse.objects.filter(session=session).values_list("question_id", flat=True)
    )
    scenario_progress = []
    for sc in scenarios:
        total = sc.questions.count()
        answered = sc.questions.filter(id__in=answered_ids).count()
        percent = int(answered / total * 100) if total else 0
        scenario_progress.append({
            "id": sc.id,
            "name": sc.name_ru,
            "answered": answered,
            "total": total,
            "percent": percent
        })
    responses = QuizResponse.objects.filter(session=session)
    selected_answers = {r.question_id: r.answer_id for r in responses if r.answer_id}

    if request.method == "POST":
        has_answer = False
        for sc in scenarios:
            for q in sc.questions.all():
                aid = request.POST.get(f"question_{q.id}")
                if aid:
                    ans = QuizAnswer.objects.filter(id=aid).first()
                    existing = QuizResponse.objects.filter(session=session, question=q).first()
                    if existing:
                        existing.answer = ans
                        existing.is_correct = ans.is_correct if ans else False
                        existing.save()
                    else:
                        QuizResponse.objects.create(
                            session=session,
                            question=q,
                            answer=ans,
                            is_correct=ans.is_correct if ans else False
                        )
                    has_answer = True

        if has_answer:
            session.logs = request.POST.get('logs', '')
            session.save()
            return redirect("quiz_preview")

        return render(request, "quiz/quiz_take.html", {
            "config": config,
            "scenarios": scenarios,
            "scenario_progress": scenario_progress,
            "error": "Пожалуйста, ответьте хотя бы на один вопрос перед отправкой.",
            "remaining_seconds": max(0, int(config.test_duration_minutes * 60 - elapsed.total_seconds())),
            "quiz_person": quiz_person,
            "selected_answers": selected_answers
        })

    return render(request, "quiz/quiz_take.html", {
        "config": config,
        "scenarios": scenarios,
        "scenario_progress": scenario_progress,
        "remaining_seconds": max(0, int(config.test_duration_minutes * 60 - elapsed.total_seconds())),
        "quiz_person": quiz_person,
        "selected_answers": selected_answers
    })


@login_required
def quiz_preview_view(request):
    person = request.user.person
    quiz_person = QuizPerson.objects.filter(person=person).first()
    session = get_object_or_404(QuizSession, person=person)
    config = QuizConfig.objects.first()

    # 1. Уже подписано → редиректим
    if quiz_person and quiz_person.signature:
        return redirect("quiz_submitted")

    # 2. Если нет ни одного ответа — редиректим обратно
    if not QuizResponse.objects.filter(session=session).exists():
        return redirect("quiz_closed")

    # 3. Рассчитываем оставшееся время
    elapsed = now() - session.started_at
    remaining_seconds = max(0, int(config.test_duration_minutes * 60 - elapsed.total_seconds()))

    # 4. Собираем сценарии, вопросы и ответы
    scenarios = Scenario.objects.prefetch_related("questions__answers").all()
    responses = QuizResponse.objects.filter(session=session).select_related("question", "answer")

    preview = []
    preview_data = []

    for sc in scenarios:
        items = []
        for q in sc.questions.all():
            resp = responses.filter(question=q).first()
            answer_text = resp.answer.name_ru if resp and resp.answer else "—"
            items.append({
                "question_id": q.id,
                "question": q.name_ru,
                "answer": answer_text,
                "is_correct": resp.is_correct if resp else False
            })
        preview.append({
            "scenario": sc,
            "items": items
        })
        preview_data.append({
            "scenario_id": sc.id,
            "scenario": sc.name_ru,
            "items": items
        })

    preview_json = json.dumps(preview_data, ensure_ascii=False)

    return render(request, "quiz/quiz_preview.html", {
        "config": config,
        "quiz_person": quiz_person,
        "preview": preview,
        "preview_json": preview_json,
        "remaining_seconds": remaining_seconds,
        "allow_submit": True
    })


@csrf_exempt
@login_required
def finalize_signed_quiz(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Метод не поддерживается"}, status=405)
    try:
        signature = request.POST.get("signature")
        if not signature:
            return JsonResponse({"success": False, "message": "Нет данных подписи"}, status=400)

        person = request.user.person
        quiz_person = QuizPerson.objects.filter(person=person).first()

        # Собираем оригинальный JSON так же, как в preview
        session = get_object_or_404(QuizSession, person=person)
        responses = QuizResponse.objects.filter(session=session)
        scenarios = Scenario.objects.prefetch_related("questions__answers").all()

        preview_data = []
        for sc in scenarios:
            items = []
            for q in sc.questions.all():
                resp = responses.filter(question=q).first()
                answer_text = resp.answer.name_ru if resp and resp.answer else "—"
                items.append({
                    "question_id": q.id,
                    "question": q.name_ru,
                    "answer": answer_text,
                    "is_correct": resp.is_correct if resp else False
                })
            preview_data.append({"scenario_id": sc.id, "scenario": sc.name_ru, "items": items})

        original_json = json.dumps(preview_data, ensure_ascii=False)
        original_b64 = base64.b64encode(original_json.encode("utf-8")).decode("utf-8")

        # Проверка подписи через внешний сервис
        proxies = {"http": "http://sslvpn-proxy:3128", "https": "http://sslvpn-proxy:3128"}
        resp = requests.post(
            "http://192.168.28.12:14579/cms/verify",
            json={
                "cms": signature,
                "revocationCheck": ["OCSP"],
                "data": original_b64,
                "detached": True
            },
            timeout=30,
            proxies=proxies
        )
        resp.raise_for_status()
        result = resp.json()
        if not result.get("valid"):
            return JsonResponse({"success": False, "message": "Подпись не прошла проверку"})

        # Сохраняем оригинальные данные и сам ключ в QuizPerson
        quiz_person.signature_data = original_json
        quiz_person.signature = signature
        quiz_person.save()

        # Финализируем сессию
        session.submitted_at = now()
        session.is_submitted = True
        session.save()

        return JsonResponse({"success": True, "message": "Тест успешно подписан и отправлен"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
def quiz_closed_view(request):
    config = QuizConfig.objects.first()
    return render(request, "quiz/quiz_closed.html", {"config": config})


@login_required
def quiz_already_submitted_view(request):
    return render(request, "quiz/quiz_already_submitted.html")


@login_required
def quiz_submitted_view(request):
    return render(request, "quiz/quiz_submitted.html")


GENDER_MAPPING = {
    "male": 1,
    "female": 2,
}
LANGUAGE_MAPPING = {
    "english": 1,
    "kazakh": 2,
    "russian": 3,
}

@staff_member_required
@login_required
def quiz_results_view(request):
    # собираем все вопросы (для заголовков Q1…QN)
    questions = list(QuizQuestion.objects.order_by('id'))
    # все сданные сессии
    sessions = (
        QuizSession.objects
        .filter(is_submitted=True)
        .select_related('person__quizperson')
        .prefetch_related('responses__answer')
    )

    rows = []
    for sess in sessions:
        qp = getattr(sess.person, 'quizperson', None)
        # личные поля
        ext_id = qp.external_id if qp else ""
        fn = qp.firstname if qp else ""
        ln = qp.lastname if qp else ""
        gender = GENDER_MAPPING.get(qp.gender, "") if qp else ""
        age = qp.age if qp else ""
        exp = qp.years_experience if qp else ""
        texp = qp.teaching_experience if qp else ""
        edu = qp.education_id if qp else ""
        reg = qp.region_id if qp else ""
        lang = LANGUAGE_MAPPING.get(qp.language, "") if qp else ""
        # ответы: {question_id: external_id}
        resp_map = {
            r.question_id: (r.answer.external_id if r.answer else "")
            for r in sess.responses.all()
        }
        answers = [resp_map.get(q.id, "") for q in questions]

        rows.append({
            'external_id': ext_id,
            'firstname': fn,
            'lastname': ln,
            'gender': gender,
            'age': age,
            'years_experience': exp,
            'teaching_experience': texp,
            'education': edu,
            'region': reg,
            'language': lang,
            'answers': answers,
        })

    return render(request, "quiz/quiz_results.html", {
        "questions": questions,
        "rows": rows,
    })


@login_required
def export_results_csv(request):
    questions = list(QuizQuestion.objects.order_by('id'))
    sessions = (
        QuizSession.objects
        .filter(is_submitted=True)
        .select_related('person__quizperson')
        .prefetch_related('responses__answer')
    )
    # настройки HTTP-ответа для CSV
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="quiz_results.csv"'
    writer = csv.writer(response)
    # заголовок
    header = [
                 "Id", "First name", "Last name",
                 "Gender", "Age", "YearsExperience","TeachingExperience",
                 "Education", "Region","Language"
             ] + [f"Q{i + 1}" for i in range(len(questions))]
    writer.writerow(header)

    for sess in sessions:
        qp = getattr(sess.person, 'quizperson', None)
        ext_id = qp.external_id if qp else ""
        fn = qp.firstname if qp else ""
        ln = qp.lastname if qp else ""
        gender = GENDER_MAPPING.get(qp.gender, "") if qp else ""
        age = qp.age if qp else ""
        exp = qp.years_experience if qp else ""
        texp = qp.teaching_experience if qp else ""
        edu = qp.education_id if qp else ""
        reg = qp.region_id if qp else ""
        lang = LANGUAGE_MAPPING.get(qp.language, "") if qp else ""
        resp_map = {
            r.question_id: (r.answer.external_id if r.answer else "")
            for r in sess.responses.all()
        }
        answers = [resp_map.get(q.id, "") for q in questions]

        writer.writerow([
            ext_id, fn, ln, gender, age, exp,texp, edu, reg,lang, *answers
        ])

    return response


@login_required
def export_results_excel(request):
    questions = list(QuizQuestion.objects.order_by('id'))
    sessions = (
        QuizSession.objects
        .filter(is_submitted=True)
        .select_related('person__quizperson')
        .prefetch_related('responses__answer')
    )
    wb = Workbook()
    ws = wb.active
    # заголовок
    ws.append([
                  "Id", "First name", "Last name",
                  "Gender", "Age", "YearsExperience", "TeachingExperience",
                  "Education", "Region", "Language"
              ] + [f"Q{i + 1}" for i in range(len(questions))])

    for sess in sessions:
        qp = getattr(sess.person, 'quizperson', None)
        ext_id = qp.external_id if qp else ""
        fn = qp.firstname if qp else ""
        ln = qp.lastname if qp else ""
        gender = GENDER_MAPPING.get(qp.gender, "") if qp else ""
        age = qp.age if qp else ""
        exp = qp.years_experience if qp else ""
        texp = qp.teaching_experience if qp else ""
        edu = qp.education_id if qp else ""
        reg = qp.region_id if qp else ""
        lang = LANGUAGE_MAPPING.get(qp.language, "") if qp else ""
        resp_map = {
            r.question_id: (r.answer.external_id if r.answer else "")
            for r in sess.responses.all()
        }
        answers = [resp_map.get(q.id, "") for q in questions]

        ws.append([ext_id, fn, ln, gender, age, exp,texp, edu, reg,lang, *answers])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    response = HttpResponse(
        stream,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="quiz_results.xlsx"'
    return response
