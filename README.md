# Onboarding Checklist

Een losse Alliance Auth-plugin die een **onboarding-checklist** als widget op het
dashboard toont. De stappen worden **automatisch** afgevinkt op basis van AA
(main character), django-esi (tokens/clones) en optioneel de Discord-service —
volledig zelfstandig, geen afhankelijkheid van andere plugins.

## Stappen (instelbaar in de admin)

- **Register main character** — main via SSO gekoppeld
- **Link character (ESI)** — token met `esi-clones.read_clones.v1` aanwezig
- **Link Discord account** — alleen als de Discord-service actief is
- **Set death clone to staging** — home/death-clone op de ingestelde staging-locatie
- **Configure jump clone placements** — minstens N jump clones

## Installatie

```bash
pip install aa-onboarding-checklist
```

```python
# myauth/settings/local.py
INSTALLED_APPS += ["onboardingchecklist"]
```

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Stel daarna de staging-locatie in via **Admin → Onboarding Checklist → Instellingen**.
De widget verschijnt op het dashboard van elke ingelogde gebruiker en verdwijnt zodra
de checklist volledig is afgerond.

## Permissies

| Permissie | Voor |
|---|---|
| `onboardingchecklist.manage_settings` | mag de instellingen beheren |

## Afhankelijkheden

`allianceauth>=5`, `django-esi>=8`.
