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
            "fields": ("staging_location_id",),
        }),
        ("Jump clones", {
            "fields": ("min_jump_clones",),
        }),
    )

    actions = ("refresh_candidates",)

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
            choices = [("", "— (geen)")]
            choices += [(str(lid), f"{name} ({cnt})") for lid, name, cnt in cands]
            current = Config.load().staging_location_id
            if current and str(current) not in {c[0] for c in choices}:
                choices.insert(1, (str(current), f"Locatie {current} (huidig)"))
            return forms.TypedChoiceField(
                choices=choices, coerce=int, required=False, empty_value=None,
                label=db_field.verbose_name,
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if "staging_location_id" in getattr(form, "changed_data", []):
            obj.staging_system_id = None
            if obj.staging_location_id:
                from .resolve import location_name
                obj.staging_name = location_name(obj.staging_location_id) or ""
                self.message_user(
                    request,
                    f"Staging gezet op {obj.staging_name or ('id ' + str(obj.staging_location_id))}.",
                    level=messages.SUCCESS)
            else:
                obj.staging_name = ""
        super().save_model(request, obj, form, change)

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
