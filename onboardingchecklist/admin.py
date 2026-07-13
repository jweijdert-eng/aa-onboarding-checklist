"""Admin — Onboarding Checklist instellingen (singleton)."""

from django.contrib import admin, messages

from .models import Config


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Weergave", {
            "fields": ("hide_when_complete",),
        }),
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Automatisch de staging-naam omzetten naar een id (alleen als er nog geen id is)
        if obj.staging_name and not obj.staging_location_id and not obj.staging_system_id:
            from .resolve import resolve_staging
            res = resolve_staging(obj.staging_name)
            if res:
                obj.staging_system_id = res["system_id"]
                obj.staging_location_id = res["location_id"]
                if res.get("name"):
                    obj.staging_name = res["name"]
                obj.save()
                kind = "systeem" if res["system_id"] else "structure"
                self.message_user(
                    request,
                    f"Staging automatisch herkend als {kind}: {obj.staging_name} "
                    f"(id {res['system_id'] or res['location_id']}).",
                    level=messages.SUCCESS)
            else:
                self.message_user(
                    request,
                    f"Kon '{obj.staging_name}' niet automatisch vinden — vul het id handmatig in "
                    f"(structures worden gematcht tegen locaties waar members clones hebben).",
                    level=messages.WARNING)
