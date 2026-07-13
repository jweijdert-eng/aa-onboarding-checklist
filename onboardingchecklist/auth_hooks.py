"""Hook into Alliance Auth — dashboard-widget + urls."""

from allianceauth import hooks
from allianceauth.services.hooks import UrlHook

from . import urls
from .views import dashboard_widget


class OnboardingDashboardHook(hooks.DashboardItemHook):
    """Toon de onboarding-checklist bovenaan het AA-dashboard."""

    def __init__(self):
        super().__init__(view_function=dashboard_widget, order=1)


@hooks.register("dashboard_hook")
def register_dashboard():
    return OnboardingDashboardHook()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "onboardingchecklist", r"^onboarding/")
