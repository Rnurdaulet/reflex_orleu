import base64
import json

import requests
from base64 import b64decode
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render

from apps.people.models import Person  # замените на актуальный импорт

NCANODE_URL = "http://192.168.28.12:14579/cms/verify"


def extract_iin_from_cert(subject_dn):
    for part in subject_dn.split(','):
        part = part.strip()
        if part.startswith("SERIALNUMBER=IIN"):
            return part.split("=")[-1]
    return None


def login_via_signature(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Метод не поддерживается"}, status=405)

    try:
        body = json.loads(request.body)
        signed_data = body.get("signedData")
        if not signed_data:
            return JsonResponse({"success": False, "message": "Подпись не предоставлена"}, status=400)
        proxies = {
            "http": "http://sslvpn-proxy:3128",
            "https": "http://sslvpn-proxy:3128"
        }
        # Проверка подписи через NCANode
        response = requests.post(NCANODE_URL, json={
            "cms": signed_data,
            "revocationCheck": ["OCSP"]
        }, timeout=15,    proxies=proxies)
        response.raise_for_status()
        data = response.json()

        if not data.get("signers") or not data["signers"][0].get("certificates"):
            return JsonResponse({"success": False, "message": "Не удалось извлечь сертификат"}, status=400)

        cert = data["signers"][0]["certificates"][0]
        subject = cert.get("subject", {})
        iin = subject.get("iin")
        full_name = subject.get("commonName")

        if not iin:
            return JsonResponse({"success": False, "message": "ИИН не найден в сертификате"}, status=400)

        # Проверка или создание пользователя
        user = User.objects.filter(username=iin).first()
        if not user:
            user = User.objects.create_user(username=iin)

        # Проверка или создание/обновление Person
        person = Person.objects.filter(iin=iin).first()
        if not person:
            person = Person.objects.create(
                iin=iin,
                full_name=full_name,
                signature=signed_data,
                user=user
            )
        else:
            person.full_name = full_name
            person.signature = signed_data
            if not person.user:
                person.user = user
            person.save()

        login(request, user)

        return JsonResponse({
            "success": True,
            "redirectUrl": "/survey/",
            "fullName": full_name
        })

    except requests.exceptions.RequestException as e:
        return JsonResponse({"success": False, "message": f"Ошибка связи с NCANode: {str(e)}"}, status=502)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Ошибка: {str(e)}"}, status=500)



def signature_login_page(request):
    return render(request, "people/signature_login.html")

def home_page(request):
    return render(request, "home.html")

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect("/")


from django.contrib.auth.views import LoginView
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    template_name = "login_password.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_staff:
            return "/survey/list"
        return "/"

