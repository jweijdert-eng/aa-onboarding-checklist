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


def _linkcheck(user):
    """Wat zegt de Link Check-plugin over dit account? None = plugin er niet.

    Die plugin weet welke CharLink-koppelingen jullie verplicht stellen en of een
    token ingetrokken is. Per character: (is het goed, wat mist er).
    """
    try:
        from linkcheck.compliance import account_detail
        detail = account_detail(user)
    except Exception:  # noqa: BLE001 — plugin niet geinstalleerd of geen rechten
        return None
    if not detail:
        return None
    uit = {}
    for rij in detail.get("characters", []):
        compleet = rij["n_total"] == 0 or rij["n_linked"] == rij["n_total"]
        goed = compleet and not rij["revoked"]
        uit[rij["name"]] = (goed, "token ingetrokken" if rij["revoked"]
                            else ("" if goed
                                  else f"{rij['n_linked']}/{rij['n_total']} koppelingen"))
    return uit


def _koppel_url():
    """Waar stuur je iemand heen om te koppelen.

    CharLink als die er is: daar koppel je in een keer al je characters en meteen
    voor alle plugins die scopes vragen. Reverse in plaats van een vaste URL,
    zodat het lokaal en op dutchlegions.nl allebei klopt; zonder CharLink de
    eigen SSO-flow.
    """
    try:
        return reverse("charlink:index")
    except Exception:  # noqa: BLE001 — CharLink niet geinstalleerd
        return reverse("onboardingchecklist:link_esi")


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
    steps = [{
        "name": "Register main character",
        "desc": "Koppel je main EVE-character via SSO.",
        "auto": True, "done": bool(main), "sub": [], "note": "",
        # De knop blijft staan als je main er al is: je alts koppel je op
        # dezelfde plek.
        "url": _koppel_url(), "url_label": "Koppel via CharLink",
    }]
    if not main:
        return _finish(steps)

    cid = main.character_id
    linked = clone_token(cid) is not None

    if cfg.require_scopes:
        steps.append({
            "name": "Link character (ESI)",
            "desc": "Verleen clone-toegang (esi-clones) voor je main.",
            "auto": True, "done": linked, "sub": [],
            "note": "" if linked else "clone-toegang nog niet verleend",
            "url": None if linked else reverse("onboardingchecklist:link_esi"),
            "url_label": "Koppel nu",
        })

    if cfg.require_linkcheck:
        stand = _linkcheck(user)
        if stand is not None:
            # Alleen wie er nog niet is: de regels zijn een to-do-lijstje, en wie
            # klaar is hoeft er niet bij te staan.
            mist = [{"name": naam, "done": False, "note": uitleg, "icon_url": "",
                     "icon_text": "", "icon_size": 26}
                    for naam, (goed, uitleg) in sorted(stand.items()) if not goed]
            steps.append({
                "name": "Link Character Check",
                "desc": "Al je characters gekoppeld zoals de corp het vraagt.",
                "auto": True, "done": not mist, "sub": mist,
                "note": "" if not mist else f"{len(mist)} character(s) niet compleet",
                "url": None if not mist else _koppel_url(),
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
        clones = get_clones(cid) or {}
        home = clones.get("home_location") or {}
        jumps = clones.get("jump_clones") or []

        if cfg.require_home_clone:
            stagings = list(cfg.staging_locations.all())
            configured = bool(stagings)
            home_lid = home.get("location_id")
            done = configured and any(home_lid == s.location_id for s in stagings)
            subs = [_loc_sub(s, home_lid == s.location_id) for s in stagings]
            steps.append({
                "name": "Set death clone to staging",
                "desc": "Zet je home/death-clone op één van de staging-locaties.",
                "auto": configured, "done": done,
                "note": ("" if linked else "clone-toegang nodig — zie de stap hierboven"),
                "sub": subs,
            })

        if cfg.require_jump_clones:
            count = len(jumps)
            jump_lids = {(j or {}).get("location_id") for j in jumps}
            required = list(cfg.jump_clone_locations.all())
            if required:
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
                    "desc": f"Zorg voor minstens {cfg.min_jump_clones or 1} jump clone(s).",
                    "auto": True, "done": count >= (cfg.min_jump_clones or 1),
                    "note": (f"{count} jump clone(s)" if linked else ""), "sub": [],
                })

    return _finish(steps)
