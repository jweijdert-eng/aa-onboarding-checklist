# Onboarding Checklist

Een losse Alliance Auth-plugin die een **onboarding-checklist** als widget op het
dashboard toont. De stappen worden **automatisch** afgevinkt op basis van AA
(main character), django-esi (tokens/clones) en optioneel de Discord-/TeamSpeak-services —
volledig zelfstandig, geen afhankelijkheid van andere plugins.

## Stappen (elke stap aan/uit te zetten in de admin)

- **Register main character** — main via SSO gekoppeld
- **Link character (ESI)** — token met `esi-clones.read_clones.v1` aanwezig
- **Link Discord account** — alleen als de Discord-service actief is
- **Link TeamSpeak** — alleen als de TeamSpeak3-service actief is
- **Set death clone to staging** — home/death-clone op één van de ingestelde staging-locaties
- **Configure jump clone placements** — een jump clone op elke vereiste locatie
  (of, zonder specifieke locaties, minstens N jump clones)

Staging- en jump-clone-locaties beheer je in de admin: kies uit een dropdown van
locaties waar leden clones hebben, of beheer een eigen locatie-lijst. Per regel kun je
een **icoon** (trefwoord zoals `war`, een image-URL of een emoji) en **grootte** instellen.

## Installatie

```bash
pip install git+https://github.com/jweijdert-eng/aa-onboarding-checklist.git
```

```python
# myauth/settings/local.py
INSTALLED_APPS += ["onboardingchecklist"]
```

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Stel daarna de staging-/jump-clone-locaties in via **Admin → Onboarding Checklist → Instellingen**.
De widget verschijnt op het dashboard van elke ingelogde gebruiker en verdwijnt zodra
de checklist volledig is afgerond (tenzij je 'm altijd zichtbaar laat).

## Permissies

| Permissie | Voor |
|---|---|
| `onboardingchecklist.basic_access` | mag de eigen onboarding-checklist zien |
| `onboardingchecklist.manage_settings` | mag de instellingen beheren |

## Afhankelijkheden

`allianceauth>=5`, `django-esi>=8`.
