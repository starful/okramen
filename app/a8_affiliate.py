"""A8.net affiliate banners for OK Ramen — Agoda Partners only."""

from __future__ import annotations

import os
from typing import Any

_BANNERS: dict[str, dict[str, str]] = {
    "agoda": {
        "id": "agoda",
        "click_url": "",
        "image_url": "",
        "pixel_url": "",
        "label_en": "Agoda — hotels for ramen trips",
        "label_ko": "Agoda — 라멘 여행 숙소",
        "desc_en": "Stay near this shop or plan a multi-city ramen tour.",
        "desc_ko": "라멘 여행 숙소 예약.",
        "alt_en": "Agoda — hotels",
        "alt_ko": "Agoda — 숙소",
    },
}


def _enabled() -> bool:
    return os.getenv("A8_OKRAMEN_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _copy(
    banner_id: str,
    *,
    lang: str,
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, str]:
    src = _BANNERS[banner_id]
    is_ko = (lang or "en").lower() in ("ko", "kr")
    suffix = "ko" if is_ko else "en"
    if banner_id == "agoda":
        try:
            from agoda_partners import url_for_location
        except ImportError:
            from .agoda_partners import url_for_location
        click = url_for_location(
            lang=lang,
            lat=lat,
            lng=lng,
            country="jp",
            default_city=5085,
        )
        return {
            "id": src["id"],
            "click_url": click,
            "image_url": "",
            "pixel_url": "",
            "label": src[f"label_{suffix}"],
            "desc": src[f"desc_{suffix}"],
            "alt": src[f"alt_{suffix}"],
        }
    return {
        "id": src["id"],
        "click_url": src["click_url"],
        "image_url": "",
        "pixel_url": "",
        "label": src[f"label_{suffix}"],
        "desc": src[f"desc_{suffix}"],
        "alt": src[f"alt_{suffix}"],
    }


def a8_banners_context(
    *,
    lang: str = "en",
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    if not _enabled():
        return {"show_a8_banners": False, "a8_banners": []}
    is_ko = (lang or "en").lower() in ("ko", "kr")
    banners = [_copy("agoda", lang=lang, lat=lat, lng=lng)]
    return {
        "show_a8_banners": True,
        "a8_banners": banners,
        "a8_banners_title": (
            "라멘 여행 제휴" if is_ko else "Ramen trip partners"
        ),
        "a8_banners_note": (
            "제휴 광고 · 새 탭에서 열림"
            if is_ko
            else "Affiliate ads · opens in new tab"
        ),
    }
