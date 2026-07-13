"""Admin — Onboarding Checklist instellingen (singleton) + staging-locaties."""

from django.contrib import admin, messages

from .models import Config, JumpCloneLocation, StagingLocation


def _location_choices(include_ids=()):
    """Dropdown-keuzes: bekende member-clone-locaties + eventueel extra ids."""
    from django import forms  # noqa: F401
    try:
        from .resolve import location_candidates
        cands = location_candidates()
    except Exception:  # noqa: BLE001
        cands = []
    choices = [("", "— (kies locatie)")]
    seen = set()
    for lid, name, cnt in cands:
        choices.append((str(lid), f"{name} ({cnt})"))
        seen.add(str(lid))
    for lid in include_ids:
        if lid and str(lid) not in seen:
            choices.append((str(lid), f"Locatie {lid}"))
            seen.add(str(lid))
    return choices


class _LocationInline(admin.TabularInline):
    """Gedeelde inline met een locatie-dropdown."""

    extra = 1
    fields = ("location_id",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "location_id":
            from django import forms
            existing = list(self.model.objects.values_list("location_id", flat=True))
            return forms.TypedChoiceField(
                choices=_location_choices(existing), coerce=int, required=True,
                label=db_field.verbose_name,
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class StagingLocationInline(_LocationInline):
    model = StagingLocation


class JumpCloneLocationInline(_LocationInline):
    model = JumpCloneLocation


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    inlines = (StagingLocationInline, JumpCloneLocationInline)
    fieldsets = (
        ("Weergave", {
            "fields": ("hide_when_complete",),
        }),
        ("Actieve stappen", {
            "fields": ("require_scopes", "require_discord", "require_teamspeak",
                       "require_home_clone", "require_jump_clones"),
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

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, (StagingLocation, JumpCloneLocation)) and obj.location_id and not obj.name:
                from .resolve import location_name
                obj.name = location_name(obj.location_id) or ""
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

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
