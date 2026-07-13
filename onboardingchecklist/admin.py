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

    actions = ("refresh_candidates",)

    @admin.display(description="Herkend als")
    def staging_resolved(self, obj):
        if obj.staging_location_id:
            name = ""
            try:
                from .resolve import location_name
                name = location_name(obj.staging_location_id) or ""
            except Exception:  # noqa: BLE001
                pass
            return format_html('🏰 <b>Structure</b> — {} id <code>{}</code>', name, obj.staging_location_id)
        if obj.staging_system_id:
            return format_html('🌌 <b>Systeem</b> — id <code>{}</code>', obj.staging_system_id)
        return format_html('<span style="color:#999">— (nog niets gekozen)</span>')

    @admin.action(description="Ververs locatielijst (dropdown)")
    def refresh_candidates(self, request, queryset):
        from django.core.cache import cache
        from .resolve import location_candidates
        cache.delete("obc_location_candidates")
        n = len(location_candidates(force=True))
        self.message_user(request, f"Locatielijst ververst — {n} locaties gevonden.", messages.SUCCESS)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "staging_location_id":
            from django import forms
            try:
                from .resolve import location_candidates
                cands = location_candidates()
            except Exception:  # noqa: BLE001
                cands = []
            choices = [("", "— (geen / typ een naam hierboven)")]
            choices += [(str(lid), f"{name} ({cnt})") for lid, name, cnt in cands]
            current = Config.load().staging_location_id
            if current and str(current) not in {c[0] for c in choices}:
                choices.insert(1, (str(current), f"Locatie {current} (huidig)"))
            return forms.TypedChoiceField(
                choices=choices, coerce=int, required=False, empty_value=None,
                label=db_field.verbose_name,
                help_text="Kies de staging-locatie (gesorteerd op aantal member-clones).",
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

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
        loc_changed = "staging_location_id" in changed
        id_edited = loc_changed or "staging_system_id" in changed

        if loc_changed and obj.staging_location_id:
            # Uit de dropdown gekozen → naam bijwerken, systeem-id wissen
            from .resolve import location_name
            nm = location_name(obj.staging_location_id)
            if nm:
                obj.staging_name = nm
            obj.staging_system_id = None
            self.message_user(
                request,
                f"Staging gezet op {obj.staging_name or ('id ' + str(obj.staging_location_id))}.",
                level=messages.SUCCESS)
        elif not obj.staging_name and not obj.staging_location_id and not obj.staging_system_id:
            pass  # niets ingesteld
        elif not obj.staging_name:
            # Naam leeg maar wel id (handmatig) → laat staan
            pass
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
