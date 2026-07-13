"""
Staging-naam → id automatisch opzoeken.

- Systeemnaam (bv. "SF-XJS") → solar_system_id via publieke ESI.
- Structure-naam (bv. "BKG-Q2 - Insidious Prime") → structure-id door te matchen
  tegen de locaties waar members al clones hebben (namen opgelost met een token
  dat de structures-scope heeft; die toegang hebben ze omdat ze er een clone hebben).
"""

import logging

import requests

from django.core.cache import cache

from .esi import CLONES_SCOPE, get_clones

logger = logging.getLogger(__name__)

_ESI = "https://esi.evetech.net/latest"
_UA = {"User-Agent": "aa-onboarding-checklist"}
STRUCT_SCOPE = "esi-universe.read_structures.v1"


def _resolve_system(name):
    try:
        r = requests.post(f"{_ESI}/universe/ids/?datasource=tranquility",
                          json=[name], headers=_UA, timeout=8)
        if r.ok:
            systems = r.json().get("systems") or []
            for s in systems:
                if (s.get("name") or "").lower() == name.lower():
                    return s.get("id")
            if systems:
                return systems[0].get("id")
    except Exception as e:  # noqa: BLE001
        logger.warning("system-resolve faalde: %s", e)
    return None


def _structure_name(location_id, character_id):
    key = f"obc_structname_{location_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    from esi.models import Token
    t = Token.objects.filter(character_id=character_id, scopes__name=STRUCT_SCOPE).first()
    name = None
    if t:
        try:
            r = requests.get(f"{_ESI}/universe/structures/{location_id}/?datasource=tranquility",
                             headers={**_UA, "Authorization": f"Bearer {t.valid_access_token()}"},
                             timeout=8)
            if r.ok:
                name = r.json().get("name")
        except Exception:  # noqa: BLE001
            pass
    if name:
        cache.set(key, name, 7 * 86400)
    return name


def _station_name(location_id):
    key = f"obc_statname_{location_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    name = None
    try:
        r = requests.get(f"{_ESI}/universe/stations/{location_id}/?datasource=tranquility",
                         headers=_UA, timeout=8)
        if r.ok:
            name = r.json().get("name")
    except Exception:  # noqa: BLE001
        pass
    cache.set(key, name or "", 7 * 86400)
    return name


def location_candidates(force=False):
    """[(location_id, naam, aantal)] van locaties waar members clones hebben,
    gesorteerd op frequentie (meest gebruikte = alliance-staging bovenaan)."""
    key = "obc_location_candidates"
    if not force:
        cached = cache.get(key)
        if cached is not None:
            return cached

    from esi.models import Token
    char_ids = list(Token.objects.filter(scopes__name=CLONES_SCOPE)
                    .values_list("character_id", flat=True).distinct())[:500]
    counts, a_char = {}, {}
    for cid in char_ids:
        cl = get_clones(cid) or {}
        for loc in [cl.get("home_location")] + (cl.get("jump_clones") or []):
            lid = (loc or {}).get("location_id")
            # Alleen player-structures (citadels); NPC-stations (60xxxxxx) zijn ruis.
            if lid and lid > 1_000_000_000_000:
                counts[lid] = counts.get(lid, 0) + 1
                a_char.setdefault(lid, cid)

    out = []
    for lid, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        name = _structure_name(lid, a_char[lid]) if lid > 1_000_000_000_000 else _station_name(lid)
        out.append((lid, name or f"Locatie {lid}", cnt))
    cache.set(key, out, 3600)
    return out


def location_name(location_id):
    # 1) handmatige lijst (KnownLocation) — heeft expliciete namen
    try:
        from .models import KnownLocation
        kl = KnownLocation.objects.filter(location_id=location_id).first()
        if kl and kl.name:
            return kl.name
    except Exception:  # noqa: BLE001
        pass
    # 2) automatisch uit member-clones
    for lid, name, _cnt in location_candidates():
        if lid == location_id:
            return name
    # 3) NPC-station (publiek)
    if 60_000_000 <= location_id < 64_000_000:
        return _station_name(location_id)
    return None


def _resolve_structure(name):
    """Match een structure-naam tegen de clone-locaties van alle members."""
    from esi.models import Token
    name_l = name.lower()
    char_ids = list(Token.objects.filter(scopes__name=CLONES_SCOPE)
                    .values_list("character_id", flat=True).distinct())[:200]
    seen = {}
    for cid in char_ids:
        cl = get_clones(cid) or {}
        for loc in [cl.get("home_location")] + (cl.get("jump_clones") or []):
            lid = (loc or {}).get("location_id")
            if lid and lid > 1_000_000_000_000:
                seen.setdefault(lid, cid)
    for lid, cid in seen.items():
        nm = _structure_name(lid, cid)
        if nm and name_l in nm.lower():
            return lid, nm
    return None, None


def resolve_staging(name):
    """→ {system_id, location_id, name} of None."""
    name = (name or "").strip()
    if not name:
        return None
    if " - " in name:  # lijkt op een station/structure-naam
        lid, nm = _resolve_structure(name)
        if lid:
            return {"system_id": None, "location_id": lid, "name": nm or name}
    sid = _resolve_system(name)
    if sid:
        return {"system_id": sid, "location_id": None, "name": name}
    lid, nm = _resolve_structure(name)
    if lid:
        return {"system_id": None, "location_id": lid, "name": nm or name}
    return None
