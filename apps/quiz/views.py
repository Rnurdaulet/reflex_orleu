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
    if not config or not config.is_active():
        return redirect("quiz_closed")

    session, created = QuizSession.objects.get_or_create(
        person=person, defaults={"is_submitted": False}
    )

    elapsed = now() - session.started_at
    if elapsed > timedelta(minutes=config.test_duration_minutes):
        if not session.is_submitted:
            session.is_submitted = True
            session.submitted_at = session.started_at + timedelta(minutes=config.test_duration_minutes)
            session.save()
        return redirect("quiz_submitted")

    if session.is_submitted:
        return redirect("quiz_already_submitted")

    # загружаем все сценарии с вопросами и ответами
    scenarios = Scenario.objects.prefetch_related("questions__answers").all()

    # считаем прогресс
    answered_ids = set(
        QuizResponse.objects
        .filter(session=session)
        .values_list("question_id", flat=True)
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

    if request.method == "POST":
        has_answer = False
        for sc in scenarios:
            for q in sc.questions.all():
                aid = request.POST.get(f"question_{q.id}")
                if aid:
                    ans = QuizAnswer.objects.filter(id=aid).first()
                    QuizResponse.objects.create(
                        session=session,
                        question=q,
                        answer=ans,
                        is_correct=ans.is_correct if ans else False
                    )
                    has_answer = True

        if has_answer:
            session.is_submitted = True
            session.submitted_at = now()

            # сохраняем логи
            logs = request.POST.get('logs', '')
            session.logs = logs

            session.save()
            return redirect("quiz_preview")

        return render(request, "quiz/quiz_take.html", {
            "config": config,
            "scenarios": scenarios,
            "scenario_progress": scenario_progress,
            "error": "Пожалуйста, ответьте хотя бы на один вопрос перед отправкой.",
            "remaining_seconds": max(0, int(config.test_duration_minutes * 60 - elapsed.total_seconds())),
            "quiz_person": quiz_person
        })

    return render(request, "quiz/quiz_take.html", {
        "config": config,
        "scenarios": scenarios,
        "scenario_progress": scenario_progress,
        "remaining_seconds": max(0, int(config.test_duration_minutes * 60 - elapsed.total_seconds())),
        "quiz_person": quiz_person
    })


@login_required
def quiz_preview_view(request):
    person = request.user.person
    session = get_object_or_404(QuizSession, person=person, is_submitted=True)
    config = QuizConfig.objects.first()
    quiz_person = QuizPerson.objects.filter(person=person).first()
    scenarios = Scenario.objects.prefetch_related("questions__answers").all()
    responses = QuizResponse.objects.filter(session=session).select_related("question", "answer")

    # Собираем для отображения и для подписи
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
        preview.append({"scenario": sc, "items": items})
        preview_data.append({"scenario_id": sc.id, "scenario": sc.name_ru, "items": items})

    preview_json = json.dumps(preview_data, ensure_ascii=False)

    return render(request, "quiz/quiz_preview.html", {
        "config": config,
        "quiz_person": quiz_person,
        "preview": preview,
        "preview_json": preview_json
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
        fn     = qp.firstname       if qp else ""
        ln     = qp.lastname        if qp else ""
        gender = qp.gender          if qp else ""
        age    = qp.age             if qp else ""
        exp    = qp.years_experience if qp else ""
        edu    = qp.education_id    if qp else ""
        reg    = qp.region_id       if qp else ""
        # ответы: {question_id: external_id}
        resp_map = {
            r.question_id: (r.answer.external_id if r.answer else "")
            for r in sess.responses.all()
        }
        answers = [resp_map.get(q.id, "") for q in questions]

        rows.append({
            'external_id':        ext_id,
            'firstname':          fn,
            'lastname':           ln,
            'gender':             gender,
            'age':                age,
            'years_experience':   exp,
            'education':          edu,
            'region':             reg,
            'answers':            answers,
        })

    return render(request, "quiz/quiz_results.html", {
        "questions": questions,
        "rows":      rows,
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
        "Gender", "Age", "YearsExperience",
        "Education", "Region"
    ] + [f"Q{i+1}" for i in range(len(questions))]
    writer.writerow(header)

    for sess in sessions:
        qp = getattr(sess.person, 'quizperson', None)
        ext_id = qp.external_id if qp else ""
        fn     = qp.firstname       if qp else ""
        ln     = qp.lastname        if qp else ""
        gender = qp.gender          if qp else ""
        age    = qp.age             if qp else ""
        exp    = qp.years_experience if qp else ""
        edu    = qp.education_id    if qp else ""
        reg    = qp.region_id       if qp else ""
        resp_map = {
            r.question_id: (r.answer.external_id if r.answer else "")
            for r in sess.responses.all()
        }
        answers = [resp_map.get(q.id, "") for q in questions]

        writer.writerow([
            ext_id, fn, ln, gender, age, exp, edu, reg, *answers
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
        "Gender", "Age", "YearsExperience",
        "Education", "Region"
    ] + [f"Q{i+1}" for i in range(len(questions))])

    for sess in sessions:
        qp = getattr(sess.person, 'quizperson', None)
        ext_id = qp.external_id if qp else ""
        fn     = qp.firstname       if qp else ""
        ln     = qp.lastname        if qp else ""
        gender = qp.gender          if qp else ""
        age    = qp.age             if qp else ""
        exp    = qp.years_experience if qp else ""
        edu    = qp.education_id    if qp else ""
        reg    = qp.region_id       if qp else ""
        resp_map = {
            r.question_id: (r.answer.external_id if r.answer else "")
            for r in sess.responses.all()
        }
        answers = [resp_map.get(q.id, "") for q in questions]

        ws.append([ext_id, fn, ln, gender, age, exp, edu, reg, *answers])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    response = HttpResponse(
        stream,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="quiz_results.xlsx"'
    return response