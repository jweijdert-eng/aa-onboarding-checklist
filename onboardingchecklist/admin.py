"""Admin — Onboarding Checklist instellingen (singleton)."""

from django.contrib import admin

from .models import Config


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Actieve stappen", {
            "fields": ("require_scopes", "require_discord", "require_teamspeak",
                       "require_home_clone", "require_jump_clones"),
        }),
        ("Staging-locatie", {
            "fields": ("staging_name", "staging_location_id", "staging_system_id"),
        }),
        ("Jump clones", {
            "fields": ("min_jump_clones",),
        }),
    )

    def _can(self, request):
        return request.user.is_superuser or request.user.has_perm("onboardingchecklist.manage_settings")

    def has_view_permission(self, request, obj=None):
        return self._can(request)

    def has_change_permission(self, request, obj=None):
        return self._can(request)

    def has_add_permission(self, request):
        return self._can(request) and not Config.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
