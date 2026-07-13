"""Views — Onboarding Checklist (dashboard-widget + scope-koppeling)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from esi.decorators import token_required

from .checklist import checklist
from .esi import CLONES_SCOPE


@login_required
@token_required(scopes=[CLONES_SCOPE])
def link_esi(request, token):
    """Eenmalige SSO-flow om clone-toegang (esi-clones) te verlenen voor een character.

    django-esi slaat het token op; daarna kan de checklist de clones checken.
    """
    from django.core.cache import cache
    cache.delete(f"obc_clones_{token.character_id}")  # verse check
    messages.success(
        request,
        _("Clone-toegang gekoppeld voor %(name)s — je onboarding-checklist is bijgewerkt.")
        % {"name": token.character_name},
    )
    return redirect("authentication:dashboard")


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
