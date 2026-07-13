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
    require_home_clone = models.BooleanField(
        default=True, verbose_name=_("Stap: home/death-clone op staging"),
    )
    require_jump_clones = models.BooleanField(
        default=True, verbose_name=_("Stap: jump clones aanwezig"),
    )

    staging_name = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Staging (weergavenaam)"),
        help_text=_("Bijv. 'BKG-Q2 - Insidious Prime'."),
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
