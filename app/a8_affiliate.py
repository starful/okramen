"""Affiliate banner context for OK Ramen — Agoda Partners only.

The module/function names (``a8_banners_context``) are kept so templates and
routes keep working; A8.net itself is retired (no px.a8.net URLs or pixels).
"""

from __future__ import annotations

import os
from typing import Any

_AGODA_COPY: dict[str, str] = {
    "id": "agoda",
    "label_en": "Agoda — ramen trip hotels",
    "label_ko": "Agoda — 라멘 여행 숙소",
    "desc_en": "Stay near this shop or plan a multi-city ramen tour.",
    "desc_ko": "라멘 여행 숙소 예약.",
}


def _enabled() -> bool:
    # Prefer AFFILIATE_*; keep A8_* as legacy alias so existing .env still works.
    raw = os.getenv("AFFILIATE_OKRAMEN_ENABLED") or os.getenv("A8_OKRAMEN_ENABLED", "1")
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _agoda_banner(
    *,
    lang: str,
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, str]:
    try:
        from agoda_partners import url_for_location
    except ImportError:
        from .agoda_partners import url_for_location
    suffix = "ko" if (lang or "en").lower() in ("ko", "kr") else "en"
    return {
        "id": _AGODA_COPY["id"],
        "click_url": url_for_location(
            lang=lang,
            lat=lat,
            lng=lng,
            country="jp",
            default_city=5085,
        ),
        "label": _AGODA_COPY[f"label_{suffix}"],
        "desc": _AGODA_COPY[f"desc_{suffix}"],
    }


def a8_banners_context(
    *,
    lang: str = "en",
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    if not _enabled():
        return {
            "show_a8_banners": False,
            "a8_banners": [],
            "agoda_cta": None,
            "show_agoda_cta": False,
        }
    is_ko = (lang or "en").lower() in ("ko", "kr")
    agoda = _agoda_banner(lang=lang, lat=lat, lng=lng)
    return {
        "show_a8_banners": True,
        "a8_banners": [agoda],
        "a8_banners_title": "라멘 여행 제휴" if is_ko else "Ramen trip partners",
        "a8_banners_note": (
            "제휴 광고 · 새 탭에서 열림" if is_ko else "Affiliate ads · opens in new tab"
        ),
        "agoda_cta": agoda,
        "show_agoda_cta": True,
    }
