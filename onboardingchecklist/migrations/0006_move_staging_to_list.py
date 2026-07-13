"""Verplaats de bestaande enkele staging-locatie naar de nieuwe StagingLocation-lijst."""

from django.db import migrations


def forwards(apps, schema_editor):
    Config = apps.get_model("onboardingchecklist", "Config")
    StagingLocation = apps.get_model("onboardingchecklist", "StagingLocation")
    for cfg in Config.objects.all():
        lid = getattr(cfg, "staging_location_id", None)
        if lid and not StagingLocation.objects.filter(config=cfg, location_id=lid).exists():
            StagingLocation.objects.create(
                config=cfg, location_id=lid, name=getattr(cfg, "staging_name", "") or "",
            )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("onboardingchecklist", "0005_staginglocation"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
