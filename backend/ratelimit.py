"""
Rate limiting minimal en mémoire : par IP et global/jour.
Suffisant pour un usage démo mono-instance. Si tu passes multi-instance
ou veux un quota persistant, remplace ceci par Redis.
"""
import os
import time
from collections import defaultdict

PER_IP_MAX = int(os.environ.get("PER_IP_DAILY_MAX", "3"))
GLOBAL_MAX = int(os.environ.get("GLOBAL_DAILY_MAX", "50"))
WINDOW = 24 * 3600

_ip_hits: dict[str, list[float]] = defaultdict(list)
_global_hits: list[float] = []


class RateLimitExceeded(Exception):
    pass


def _prune(hits: list[float], now: float) -> list[float]:
    return [t for t in hits if now - t < WINDOW]


def check_and_record(ip: str) -> None:
    now = time.time()

    global _global_hits
    _global_hits = _prune(_global_hits, now)
    if len(_global_hits) >= GLOBAL_MAX:
        raise RateLimitExceeded("Quota global journalier atteint. Réessaie demain.")

    hits = _prune(_ip_hits[ip], now)
    if len(hits) >= PER_IP_MAX:
        raise RateLimitExceeded(
            f"Limite de {PER_IP_MAX} générations/jour atteinte pour cette adresse IP."
        )

    hits.append(now)
    _ip_hits[ip] = hits
    _global_hits.append(now)
