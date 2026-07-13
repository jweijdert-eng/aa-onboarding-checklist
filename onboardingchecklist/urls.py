"""URLs — Onboarding Checklist."""

from django.urls import path

from . import views

app_name = "onboardingchecklist"

urlpatterns = [
    path("link/", views.link_esi, name="link_esi"),
]
