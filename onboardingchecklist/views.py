"""Views — Onboarding Checklist (dashboard-widget)."""

from django.template.loader import render_to_string

from .checklist import checklist


def dashboard_widget(request) -> str:
    """AA-dashboard-widget: onboarding-checklist voor de ingelogde gebruiker.

    Verborgen zonder login, zonder main, of als de checklist volledig af is.
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return ""
    ob = checklist(request.user)
    if not ob.get("steps") or ob.get("complete"):
        return ""
    return render_to_string(
        "onboardingchecklist/dashboard.html", {"onboarding": ob}, request=request
    )
