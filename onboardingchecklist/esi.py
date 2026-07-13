"""Eigen (zelfstandige) ESI-toegang — geen afhankelijkheid van andere plugins."""

import logging

import requests

from django.core.cache import cache

logger = logging.getLogger(__name__)

CLONES_SCOPE = "esi-clones.read_clones.v1"
_ESI = "https://esi.evetech.net/latest"
_UA = {"User-Agent": "aa-onboarding-checklist"}
_CACHE_SECONDS = 600


def clone_token(character_id):
    """Een token voor dit character met de clones-scope, of None."""
    try:
        from esi.models import Token
        return Token.objects.filter(
            character_id=character_id, scopes__name=CLONES_SCOPE
        ).first()
    except Exception:  # noqa: BLE001
        return None


def get_clones(character_id):
    """Clones-endpoint voor een character (gecached). None = geen token/fout."""
    key = f"obc_clones_{character_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None

    token = clone_token(character_id)
    if not token:
        return None
    data = None
    try:
        access = token.valid_access_token()
        r = requests.get(
            f"{_ESI}/characters/{character_id}/clones/?datasource=tranquility",
            headers={**_UA, "Authorization": f"Bearer {access}"}, timeout=8,
        )
        if r.ok:
            data = r.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("Onboarding: clones-fetch faalde voor %s: %s", character_id, e)

    cache.set(key, data or {}, _CACHE_SECONDS)
    return data
