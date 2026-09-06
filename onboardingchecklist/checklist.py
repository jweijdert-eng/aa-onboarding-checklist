"""
Onboarding-checklist — volledig automatische stappen, zelfstandig berekend.

`checklist(user)` levert de stappen + voortgang voor één account. Gebruikt AA
(main character), django-esi (tokens/clones) en optioneel de Discord-service.
"""

from django.urls import reverse

from .esi import clone_token, get_clones
from .models import Config


def _discord_linked(user):
    """True/False of de gebruiker Discord gekoppeld heeft; None = service niet beschikbaar."""
    try:
        from allianceauth.services.modules.discord.models import DiscordUser
        return DiscordUser.objects.filter(user=user).exists()
    except Exception:  # noqa: BLE001 — service niet geïnstalleerd/ingericht
        return None


def _teamspeak_linked(user):
    """True/False of de gebruiker TeamSpeak gekoppeld heeft; None = service niet beschikbaar."""
    try:
        from allianceauth.services.modules.teamspeak3.models import Teamspeak3User
        return Teamspeak3User.objects.filter(user=user).exists()
    except Exception:  # noqa: BLE001 — service niet geïnstalleerd/ingericht
        return None


def _loc_sub(loc, done):
    """Sub-regel voor een staging/jump-clone-locatie: naam + icoon (beeld óf emoji)."""
    from .resolve import icon_image_url, location_icon, location_name
    name = loc.name or location_name(loc.location_id) or f"#{loc.location_id}"
    # Icoon: eerst het regel-eigen icoon, anders dat van de KnownLocation-lijst
    raw = getattr(loc, "icon", "") or location_icon(loc.location_id)
    img = icon_image_url(raw)
    return {
        "name": name, "done": done, "note": "Alliance requirement",
        "icon_url": img, "icon_text": "" if img else raw,
        "icon_size": getattr(loc, "icon_size", 26) or 26,
    }


def _koppel_url():
    """Waar stuur je iemand heen om te koppelen.

    CharLink als die er is: daar koppel je in een keer alle characters en meteen
    voor alle plugins die scopes vragen - de eigen SSO-flow hier doet er maar
    een, voor een enkele scope. Reverse in plaats van een vaste URL, zodat het
    lokaal en op dutchlegions.nl allebei klopt.
    """
    try:
        return reverse("charlink:index")
    except Exception:  # noqa: BLE001 — CharLink niet geinstalleerd
        return reverse("onboardingchecklist:link_esi")


def _characters(user, cfg):
    """De characters die meetellen: de main, en met 'alts meetellen' aan ook de rest.

    Alfabetisch achter de main, zodat de volgorde niet verspringt bij elke
    dashboard-lading.
    """
    main = getattr(getattr(user, "profile", None), "main_character", None)
    if not main:
        return []
    if not cfg.include_alts:
        return [main]
    alts = []
    try:
        for own in user.character_ownerships.select_related("character").all():
            char = own.character
            if char and char.character_id != main.character_id:
                alts.append(char)
    except Exception:  # noqa: BLE001 — geen ownerships is gewoon geen alts
        alts = []
    alts.sort(key=lambda c: (c.character_name or "").lower())
    return [main] + alts


def _todo(subs):
    """Alleen wat nog moet: characters die klaar zijn vallen uit de lijst.

    De regels onder een stap zijn een to-do-lijstje. Zeven groene vinkjes onder
    een stap die zelf al groen is, is alleen maar ruis - wat je wilt zien is de
    ene alt die nog niet gekoppeld is.
    """
    return [x for x in subs if not x["done"]]


def _char_sub(char, done, note="", loc=None):
    """Sub-regel voor één character; het icoon komt van de locatie waar hij staat."""
    from .resolve import icon_image_url, location_icon

    raw = ""
    if loc is not None:
        raw = getattr(loc, "icon", "") or location_icon(loc.location_id)
    img = icon_image_url(raw) if raw else ""
    return {
        "name": char.character_name, "done": done, "note": note,
        "icon_url": img, "icon_text": "" if img else raw,
        "icon_size": getattr(loc, "icon_size", 26) or 26 if loc is not None else 26,
    }


def _finish(steps):
    total = len(steps)
    done = sum(1 for s in steps if s["done"])
    return {
        "steps": steps, "done": done, "total": total,
        "pct": int(round(done / total * 100)) if total else 0,
        "complete": total > 0 and done == total,
    }


def checklist(user):
    """Onboarding-stappen + voortgang voor een account (via z'n main character)."""
    cfg = Config.load()

    main = getattr(getattr(user, "profile", None), "main_character", None)
    koppelen = _koppel_url()
    steps = [{
        "name": "Register main character",
        "desc": "Koppel je main EVE-character.",
        "auto": True, "done": bool(main), "sub": [], "note": "",
        "url": None if main else koppelen, "url_label": "Koppel via CharLink",
    }]
    if not main:
        return _finish(steps)

    cid = main.character_id
    chars = _characters(user, cfg)
    # Per character of hij clone-toegang heeft. Met alts uit is dit alleen de main.
    heeft_token = {c.character_id: clone_token(c.character_id) is not None for c in chars}
    linked = heeft_token.get(cid, False)
    alles_gekoppeld = all(heeft_token.values())
    meerdere = cfg.include_alts and len(chars) > 1
    # Per stap: gaat het over alle characters of alleen over de main? Een alt
    # parkeer je ergens anders, dus de clone-stappen staan standaard op de main.
    home_alts = meerdere and cfg.alts_home_clone
    jump_alts = meerdere and cfg.alts_jump_clones

    if cfg.require_scopes:
        mist = [c for c in chars if not heeft_token[c.character_id]]
        klaar = alles_gekoppeld if meerdere else linked
        steps.append({
            "name": "Link character (ESI)",
            "desc": ("Koppel al je characters — main én alts."
                     if meerdere else "Verleen clone-toegang (esi-clones) voor je main."),
            "auto": True, "done": klaar,
            "sub": (_todo([_char_sub(c, heeft_token[c.character_id],
                                    "" if heeft_token[c.character_id]
                                    else "geen clone-toegang")
                          for c in chars]) if meerdere else []),
            "note": "" if klaar else (f"{len(mist)} character(s) nog niet gekoppeld"
                                      if meerdere else "clone-toegang nog niet verleend"),
            "url": None if klaar else koppelen,
            "url_label": "Koppel via CharLink",
        })

    if cfg.require_discord:
        linked = _discord_linked(user)
        if linked is not None:
            steps.append({
                "name": "Link Discord account",
                "desc": "Koppel je Discord-account voor comms-toegang.",
                "auto": True, "done": linked, "sub": [], "note": "",
            })

    if cfg.require_teamspeak:
        linked = _teamspeak_linked(user)
        if linked is not None:
            steps.append({
                "name": "Link TeamSpeak",
                "desc": "Koppel je TeamSpeak-account voor voice-comms.",
                "auto": True, "done": linked, "sub": [], "note": "",
            })

    if cfg.require_home_clone or cfg.require_jump_clones:
        # Eén clones-aanvraag per character (gecached). Zonder token levert dat
        # meteen niets op, dus dat kost ook geen ESI-verzoek. Staan beide
        # clone-stappen op de main, dan halen we ook alleen die op - anders
        # betaal je ESI-verzoeken voor antwoorden die niemand bekijkt.
        te_halen = chars if (home_alts or jump_alts) else [main]
        per_char = {c.character_id: (get_clones(c.character_id) or {}) for c in te_halen}
        clones = per_char.get(cid, {})
        home = clones.get("home_location") or {}
        jumps = clones.get("jump_clones") or []

        if cfg.require_home_clone:
            stagings = list(cfg.staging_locations.all())
            configured = bool(stagings)

            def _thuis(char):
                """(staat hij goed, op welke staging) voor één character."""
                lid = ((per_char.get(char.character_id, {}).get("home_location") or {})
                       .get("location_id"))
                for s in stagings:
                    if lid == s.location_id:
                        return True, s
                return False, None

            if home_alts:
                subs, alle_goed = [], configured
                for char in chars:
                    goed, staging = _thuis(char)
                    alle_goed = alle_goed and goed
                    subs.append(_char_sub(
                        char, goed,
                        (staging.name if staging and staging.name else "")
                        if goed else ("niet op een staging-locatie"
                                      if heeft_token[char.character_id]
                                      else "geen clone-toegang"),
                        staging))
                subs = _todo(subs)
                done = alle_goed
            else:
                home_lid = home.get("location_id")
                done = configured and any(home_lid == s.location_id for s in stagings)
                subs = [_loc_sub(s, home_lid == s.location_id) for s in stagings]
            steps.append({
                "name": "Set death clone to staging",
                "desc": ("Zet de home/death-clone van elk character op een staging-locatie."
                         if home_alts
                         else "Zet je home/death-clone op één van de staging-locaties."),
                "auto": configured, "done": done,
                "note": ("" if linked else "clone-toegang nodig — zie de stap hierboven"),
                "sub": subs,
            })

        if cfg.require_jump_clones:
            count = len(jumps)
            jump_lids = {(j or {}).get("location_id") for j in jumps}
            required = list(cfg.jump_clone_locations.all())
            nodig = cfg.min_jump_clones or 1

            def _sprongen(char):
                """(voldoet hij, toelichting) voor één character."""
                lijst = per_char.get(char.character_id, {}).get("jump_clones") or []
                lids = {(j or {}).get("location_id") for j in lijst}
                if not heeft_token[char.character_id]:
                    return False, "geen clone-toegang"
                if required:
                    raak = sum(1 for r in required if r.location_id in lids)
                    return raak == len(required), f"{raak}/{len(required)} locaties"
                return len(lijst) >= nodig, f"{len(lijst)} jump clone(s)"

            if jump_alts:
                subs, alle_goed = [], True
                for char in chars:
                    goed, uitleg = _sprongen(char)
                    alle_goed = alle_goed and goed
                    subs.append(_char_sub(char, goed, uitleg))
                subs = _todo(subs)
                steps.append({
                    "name": "Configure jump clone placements",
                    "desc": ("Zorg dat elk character een jump clone op elke vereiste locatie heeft."
                             if required
                             else f"Zorg dat elk character minstens {nodig} jump clone(s) heeft."),
                    "auto": True, "done": alle_goed, "note": "", "sub": subs,
                })
            elif required:
                subs = [_loc_sub(r, r.location_id in jump_lids) for r in required]
                steps.append({
                    "name": "Configure jump clone placements",
                    "desc": "Zorg voor een jump clone op elke vereiste locatie.",
                    "auto": True, "done": all(s["done"] for s in subs),
                    "note": (f"{count} jump clone(s)" if linked else ""), "sub": subs,
                })
            else:
                steps.append({
                    "name": "Configure jump clone placements",
                    "desc": f"Zorg voor minstens {nodig} jump clone(s).",
                    "auto": True, "done": count >= nodig,
                    "note": (f"{count} jump clone(s)" if linked else ""), "sub": [],
                })

    return _finish(steps)
