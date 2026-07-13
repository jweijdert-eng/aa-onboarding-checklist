"""Admin — Onboarding Checklist instellingen (singleton)."""

from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Config


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    readonly_fields = ("staging_resolved",)
    fieldsets = (
        ("Weergave", {
            "fields": ("hide_when_complete",),
        }),
        ("Actieve stappen", {
            "fields": ("require_scopes", "require_discord", "require_teamspeak",
                       "require_home_clone", "require_jump_clones"),
        }),
        ("Staging-locatie", {
            "fields": ("staging_name", "staging_resolved",
                       "staging_location_id", "staging_system_id"),
            "description": ("Typ bij <b>Staging (naam)</b> een systeem- of structure-naam en sla op — "
                            "het juiste id wordt automatisch opgezocht en hieronder getoond. "
                            "Wijzig je de naam, dan wordt opnieuw gezocht. De id-velden zijn een "
                            "handmatige override voor als het automatisch zoeken niets vindt."),
        }),
        ("Jump clones", {
            "fields": ("min_jump_clones",),
        }),
    )

    @admin.display(description="Herkend als")
    def staging_resolved(self, obj):
        if obj.staging_location_id:
            return format_html('🏰 <b>Structure</b> — id <code>{}</code>', obj.staging_location_id)
        if obj.staging_system_id:
            return format_html('🌌 <b>Systeem</b> — id <code>{}</code>', obj.staging_system_id)
        return format_html('<span style="color:#999">— (nog niets herkend; typ een naam en sla op)</span>')

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
        changed = getattr(form, "changed_data", [])
        name_changed = "staging_name" in changed
        id_edited = "staging_location_id" in changed or "staging_system_id" in changed

        if not obj.staging_name:
            # Naam leeg → geen staging
            obj.staging_location_id = None
            obj.staging_system_id = None
        elif name_changed or (not obj.staging_location_id and not obj.staging_system_id):
            from .resolve import resolve_staging
            res = resolve_staging(obj.staging_name)
            if res:
                obj.staging_system_id = res["system_id"]
                obj.staging_location_id = res["location_id"]
                if res.get("name"):
                    obj.staging_name = res["name"]
                kind = "systeem" if res["system_id"] else "structure"
                self.message_user(
                    request,
                    f"Staging herkend als {kind}: {obj.staging_name} "
                    f"(id {res['system_id'] or res['location_id']}).",
                    level=messages.SUCCESS)
            else:
                # Niet gevonden: stale id's opruimen bij naamswijziging (tenzij handmatig gezet)
                if name_changed and not id_edited:
                    obj.staging_location_id = None
                    obj.staging_system_id = None
                self.message_user(
                    request,
                    f"Kon '{obj.staging_name}' niet automatisch vinden — vul het station/structure-id "
                    f"handmatig in (structures worden gematcht tegen locaties waar members clones hebben).",
                    level=messages.WARNING)

        super().save_model(request, obj, form, change)
