"""Amazon JP Associates — content-kind search links (tag=starful06-22)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote_plus

TAG = os.getenv("AMAZON_JP_TAG", "starful06-22")

# kind → Japanese search keyword (Amazon.co.jp)
_KEYWORDS: dict[str, str] = {
    "default": "ラーメン グッズ",
    "shop": "ラーメン グッズ",
    "guide": "ラーメン 道具",
    "instant": "袋麺 おすすめ",
}

# kind → (label_en, label_ko, desc_en, desc_ko)
_COPY: dict[str, tuple[str, str, str, str]] = {
    "default": (
        "Amazon — ramen goods",
        "Amazon — 라멘 굿즈",
        "Bowls, instant ramen and ramen gifts.",
        "라멘 그릇·인스턴트 라멘·선물.",
    ),
    "guide": (
        "Amazon — ramen tools",
        "Amazon — 라멘 도구",
        "Bowls, spoons, strainers and cooking gear.",
        "그릇·숟가락·뜰채 등 라멘 조리 도구.",
    ),
    "instant": (
        "Amazon — instant ramen picks",
        "Amazon — 봉지라면 추천",
        "Popular packaged noodles from Japan.",
        "일본 인기 봉지라면.",
    ),
}
_COPY["shop"] = _COPY["default"]


def search_url(keyword: str) -> str:
    k = (keyword or "").strip() or _KEYWORDS["default"]
    return (
        f"https://www.amazon.co.jp/s?k={quote_plus(k)}"
        f"&tag={TAG}&linkCode=ll2&ref_=as_li_ss_tl"
    )


def _enabled() -> bool:
    return os.getenv("AMAZON_OKRAMEN_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def amazon_context(*, kind: str = "default", lang: str = "en") -> dict[str, Any]:
    if not _enabled():
        return {"show_amazon": False, "amazon_cta": None}
    key = (kind or "default").strip().lower() or "default"
    if key not in _KEYWORDS:
        key = "default"
    keyword = _KEYWORDS[key]
    is_ko = (lang or "en").lower() in ("ko", "kr")
    label_en, label_ko, desc_en, desc_ko = _COPY[key]
    return {
        "show_amazon": True,
        "amazon_cta": {
            "id": "amazon",
            "click_url": search_url(keyword),
            "label": label_ko if is_ko else label_en,
            "desc": desc_ko if is_ko else desc_en,
            "keyword": keyword,
        },
    }
