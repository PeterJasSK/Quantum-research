from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile_page, name="profile_page"),
    path("history_page/", views.history_page, name="history_page"),
    path("users_page/", views.users_page, name="users_page"),

]
