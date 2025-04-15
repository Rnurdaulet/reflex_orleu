from django.urls import path
from .views import login_via_signature, signature_login_page

urlpatterns = [
    path("signature/login", login_via_signature, name="signature_login"),
    path("signature", signature_login_page, name="signature_login_page"),
]
