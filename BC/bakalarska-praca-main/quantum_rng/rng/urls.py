# rng/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.main_page, name="main_page"),
    path("coin/", views.coin_page, name="coin_page"),
    path("dice/", views.dice_page, name="dice_page"),
    path("generator/", views.generator_page, name="generator_page"),
    path("about/", views.about_page, name="about_page"),
    path("api/", views.api_page, name="api_page"),
    path("charts/", views.charts_page, name="charts_page"),
    path("administration/", views.administration_page, name="administration_page")
]