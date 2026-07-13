"""Models — Onboarding Checklist."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class General(models.Model):
    """Meta-model voor permissies."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", _("Kan de eigen onboarding-checklist zien")),
            ("manage_settings", _("Kan de onboarding-instellingen beheren")),
        )


class Config(models.Model):
    """Eén rij met instellingen, bewerkbaar via het admin-paneel."""

    require_scopes = models.BooleanField(
        default=True, verbose_name=_("Stap: character/ESI koppelen"),
        help_text=_("Vraag om het koppelen van het character (esi-clones-scope)."),
    )
    require_discord = models.BooleanField(
        default=True, verbose_name=_("Stap: Discord koppelen"),
        help_text=_("Alleen zichtbaar als de Discord-service is geïnstalleerd."),
    )
    require_teamspeak = models.BooleanField(
        default=True, verbose_name=_("Stap: TeamSpeak koppelen"),
        help_text=_("Alleen zichtbaar als de TeamSpeak3-service is geïnstalleerd."),
    )
    require_home_clone = models.BooleanField(
        default=True, verbose_name=_("Stap: home/death-clone op staging"),
    )
    require_jump_clones = models.BooleanField(
        default=True, verbose_name=_("Stap: jump clones aanwezig"),
    )

    hide_when_complete = models.BooleanField(
        default=False, verbose_name=_("Widget verbergen bij 100% voltooid"),
        help_text=_("Uit (standaard): de checklist blijft altijd zichtbaar, met een "
                    "'voltooid'-melding zodra alles klaar is. Aan: verbergt de widget bij 100%."),
    )

    staging_name = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Staging (naam)"),
        help_text=_("Typ een systeem- of structure-naam en laat de id-velden leeg: bij opslaan "
                    "wordt het id automatisch opgezocht. Systeem = bv. 'SF-XJS'; structure = bv. "
                    "'BKG-Q2 - Insidious Prime' (met ' - ')."),
    )
    staging_system_id = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Staging solar system id"),
        help_text=_("Home/death-clone in dit systeem = afgevinkt (werkt voor NPC-stations)."),
    )
    staging_location_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Staging station/structure id"),
        help_text=_("Exacte station- of structure-id (citadel). Meest betrouwbaar, ook voor "
                    "player-structures. Home-clone hier = afgevinkt."),
    )
    min_jump_clones = models.PositiveSmallIntegerField(
        default=1, verbose_name=_("Min. aantal jump clones"),
    )

    class Meta:
        default_permissions = ()
        verbose_name = _("instellingen")
        verbose_name_plural = _("instellingen")

    def __str__(self) -> str:
        return "Onboarding Checklist instellingen"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "Config":
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class StagingLocation(models.Model):
    """Eén staging-locatie (station/structure). Meerdere mogelijk."""

    config = models.ForeignKey(
        Config, on_delete=models.CASCADE, related_name="staging_locations",
    )
    location_id = models.BigIntegerField(verbose_name=_("Station/structure id"))
    name = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        default_permissions = ()
        verbose_name = _("staging-locatie")
        verbose_name_plural = _("staging-locaties")

    def __str__(self) -> str:
        return self.name or f"#{self.location_id}"


class JumpCloneLocation(models.Model):
    """Eén vereiste jump-clone-locatie (station/structure). Meerdere mogelijk."""

    config = models.ForeignKey(
        Config, on_delete=models.CASCADE, related_name="jump_clone_locations",
    )
    location_id = models.BigIntegerField(verbose_name=_("Station/structure id"))
    name = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        default_permissions = ()
        verbose_name = _("jump-clone-locatie")
        verbose_name_plural = _("jump-clone-locaties")

    def __str__(self) -> str:
        return self.name or f"#{self.location_id}"
