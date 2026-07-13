"""
Onboarding-checklist — volledig automatische stappen, zelfstandig berekend.

`checklist(user)` levert de stappen + voortgang voor één account. Gebruikt AA
(main character), django-esi (tokens/clones) en optioneel de Discord-service.
"""

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
    }]
    if not main:
        return _finish(steps)

    cid = main.character_id
    linked = clone_token(cid) is not None

    if cfg.require_scopes:
        steps.append({
            "name": "Link character (ESI)",
            "desc": "Koppel je character zodat we je clones kunnen checken (esi-clones).",
            "auto": True, "done": linked, "sub": [],
            "note": "" if linked else "koppel via CharLink",
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
            configured = bool(cfg.staging_location_id or cfg.staging_system_id)
            done = configured and _home_at_staging(home, cfg)
            staging_label = cfg.staging_name or (
                f"systeem #{cfg.staging_system_id}" if cfg.staging_system_id else
                (f"locatie #{cfg.staging_location_id}" if cfg.staging_location_id else None))
            steps.append({
                "name": "Set death clone to staging",
                "desc": "Zet je home/death-clone op de staging-locatie.",
                "auto": configured, "done": done,
                "note": ("" if linked else "koppel eerst je character"),
                "sub": ([{"name": staging_label, "done": done, "note": "Alliance requirement"}]
                        if staging_label else []),
            })

        if cfg.require_jump_clones:
            count = len(jumps)
            steps.append({
                "name": "Configure jump clone placements",
                "desc": f"Zorg voor minstens {cfg.min_jump_clones or 1} jump clone(s).",
                "auto": True, "done": count >= (cfg.min_jump_clones or 1),
                "note": (f"{count} jump clone(s)" if linked else ""), "sub": [],
            })

    return _finish(steps)


def _home_at_staging(home, cfg):
    """Home-clone op de staging-locatie? (exacte id, of systeem voor NPC-stations)."""
    loc_id = home.get("location_id")
    if not loc_id:
        return False
    if cfg.staging_location_id and loc_id == cfg.staging_location_id:
        return True
    if cfg.staging_system_id:
        return _location_system(loc_id, home.get("location_type")) == cfg.staging_system_id
    return False


def _location_system(location_id, location_type):
    """Station/structure-id → solar_system_id (publiek voor stations)."""
    from django.core.cache import cache
    import requests
    key = f"obc_locsys_{location_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    system_id = None
    try:
        if location_type == "station" or (60_000_000 <= location_id < 64_000_000):
            r = requests.get(
                f"https://esi.evetech.net/latest/universe/stations/{location_id}/?datasource=tranquility",
                headers={"User-Agent": "aa-onboarding-checklist"}, timeout=8)
            if r.ok:
                system_id = r.json().get("system_id")
    except Exception:  # noqa: BLE001
        pass
    cache.set(key, system_id or 0, 7 * 86400)
    return system_id
