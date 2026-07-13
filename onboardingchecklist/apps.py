from django.apps import AppConfig

from . import __version__


class OnboardingChecklistConfig(AppConfig):
    name = "onboardingchecklist"
    label = "onboardingchecklist"
    verbose_name = f"Onboarding Checklist v{__version__}"
    default_auto_field = "django.db.models.AutoField"
