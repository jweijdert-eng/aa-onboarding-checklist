"""Admin — Onboarding Checklist instellingen (singleton) + staging-locaties."""

from django.contrib import admin, messages

from .models import Config, JumpCloneLocation, KnownLocation, StagingLocation


def _location_choices(include_ids=()):
    """Dropdown-keuzes: automatisch gevonden member-clone-locaties + de handmatige
    lijst (KnownLocation) + eventueel al-geselecteerde ids."""
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
    icons = {kl.location_id: kl.icon for kl in KnownLocation.objects.all()}
    choices = [(v, (f"{icons[int(v)]} {lab}".strip() if v and int(v) in icons and icons[int(v)] else lab))
               for v, lab in choices]
    for kl in KnownLocation.objects.all():
        if str(kl.location_id) not in seen:
            lab = kl.name or f"Locatie {kl.location_id}"
            choices.append((str(kl.location_id), f"{kl.icon} {lab}".strip() if kl.icon else lab))
            seen.add(str(kl.location_id))
    for lid in include_ids:
        if lid and str(lid) not in seen:
            choices.append((str(lid), f"Locatie {lid}"))
            seen.add(str(lid))
    return choices


@admin.register(KnownLocation)
class KnownLocationAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "location_id")
    search_fields = ("name", "location_id")
    fields = ("location_id", "name", "icon")

    def save_model(self, request, obj, form, change):
        if obj.location_id and not obj.name:
            obj.name = _resolve_name(obj.location_id) or ""
        super().save_model(request, obj, form, change)
        from django.core.cache import cache
        cache.delete("obc_location_candidates")  # dropdowns verversen

    def _can(self, request):
        return request.user.is_superuser or request.user.has_perm("onboardingchecklist.manage_settings")

    def has_view_permission(self, request, obj=None):
        return self._can(request)

    def has_add_permission(self, request):
        return self._can(request)

    def has_change_permission(self, request, obj=None):
        return self._can(request)

    def has_delete_permission(self, request, obj=None):
        return self._can(request)


def _resolve_name(location_id):
    """Naam voor een id: eerst uit de member-clone-lijst, anders (NPC-station) publiek."""
    try:
        from .resolve import location_name, _station_name
        return location_name(location_id) or (
            _station_name(location_id) if 60_000_000 <= location_id < 64_000_000 else None)
    except Exception:  # noqa: BLE001
        return None


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
