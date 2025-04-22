from django.contrib.auth.views import LogoutView, LoginView
from django.urls import path
from .views import login_via_signature, signature_login_page, home_page, logout_view, CustomLoginView, fill_quizperson

urlpatterns = [
    path("", home_page, name="home"),
    path("logout/", logout_view, name="logout"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("signature/login", login_via_signature, name="signature_login"),
    path("signature", signature_login_page, name="signature_login_page"),
    path("fill-profile/", fill_quizperson, name="fill_quizperson"),

]
