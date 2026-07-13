"""
Staging-naam → id automatisch opzoeken.

- Systeemnaam (bv. "SF-XJS") → solar_system_id via publieke ESI.
- Structure-naam (bv. "BKG-Q2 - Insidious Prime") → structure-id door te matchen
  tegen de locaties waar members al clones hebben (namen opgelost met een token
  dat de structures-scope heeft; die toegang hebben ze omdat ze er een clone hebben).
"""

import logging

import requests

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
    from esi.models import Token
    t = Token.objects.filter(character_id=character_id, scopes__name=STRUCT_SCOPE).first()
    if not t:
        return None
    try:
        r = requests.get(f"{_ESI}/universe/structures/{location_id}/?datasource=tranquility",
                         headers={**_UA, "Authorization": f"Bearer {t.valid_access_token()}"},
                         timeout=8)
        if r.ok:
            return r.json().get("name")
    except Exception:  # noqa: BLE001
        pass
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
