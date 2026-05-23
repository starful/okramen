"""Trip-planning fields for ramen shop pages (AdSense / UX: practical-first layout)."""

from __future__ import annotations

import re

# English category slug -> display label
_STYLE_EN = {
    "tonkotsu": "Tonkotsu",
    "shoyu": "Shoyu",
    "miso": "Miso",
    "shio": "Shio",
    "tsukemen": "Tsukemen",
    "chicken": "Chicken ramen",
    "vegan": "Vegan-friendly",
    "local gem": "Local favorite",
    "late night": "Late-night",
    "premium": "Premium",
}

_STYLE_KO = {
    "tonkotsu": "돈코츠",
    "shoyu": "쇼유",
    "miso": "미소",
    "shio": "시오",
    "tsukemen": "츠케멘",
    "chicken": "치킨 라멘",
    "vegan": "비건",
    "local gem": "현지인 맛집",
    "late night": "야식",
    "premium": "프리미엄",
    "미소": "미소",
    "쇼유": "쇼유",
    "돈코츠": "돈코츠",
    "시오": "시오",
    "츠케멘": "측멘",
    "현지인맛집": "현지인 맛집",
}

_ORDER_EN = {
    "tonkotsu": "House tonkotsu ramen; add extra chashu if you want a heavier bowl.",
    "shoyu": "Classic shoyu ramen; taste the broth first before adding condiments.",
    "miso": "Miso ramen; in Sapporo-style shops, butter corn toppings are common.",
    "shio": "Shio (salt) ramen for a lighter broth; good when you want clarity over richness.",
    "tsukemen": "Tsukemen (dipping noodles); finish with soup-wari (broth top-up) if offered.",
    "chicken": "Chicken-based ramen or tori paitan; often lighter than pork-heavy bowls.",
    "vegan": "Plant-based ramen — confirm ingredients on site if you avoid fish or egg.",
    "default": "The shop’s signature bowl on the menu board; ask staff if the ticket machine is unclear.",
}

_ORDER_KO = {
    "tonkotsu": "시그니처 돈코츠 라멘; 더 든든하게 먹고 싶다면 차슈 추가를 고려하세요.",
    "shoyu": "기본 쇼유 라멘; 부가 조미료 넣기 전에 육수 맛을 먼저 확인하세요.",
    "miso": "미소 라멘; 삿포로 계열은 버터·옥수수 토핑이 흔합니다.",
    "shio": "시오(소금) 라멘 — 맑고 가벼운 맛을 원할 때.",
    "tsukemen": "츠케멘(찍어먹는 면); 가능하면 마지막에 스프 와리(육수 희석)를 요청하세요.",
    "chicken": "치킨/토리계 라멘 — 돼지뼈보다 가볍게 느껴지는 경우가 많습니다.",
    "vegan": "비건 메뉴 — 생선·달걀 알레르기가 있다면 매장에서 재료를 꼭 확인하세요.",
    "default": "메뉴판 시그니처 라멘; 키오스크가 어렵다면 직원에게 주문을 부탁하세요.",
}

_GOOD_FOR_EN = {
    "tonkotsu": "Rich-broth lovers, first-time Japan ramen visitors",
    "shoyu": "Classic ramen fans, travelers who prefer balanced bowls",
    "miso": "Cold-weather days, Hokkaido-style comfort food",
    "shio": "Light eaters, seafood-forward broth fans",
    "tsukemen": "Noodle-texture fans, repeat visitors to Tokyo",
    "default": "Trip planning before you land; not a substitute for the shop’s official info",
}

_GOOD_FOR_KO = {
    "tonkotsu": "진한 국물을 좋아하는 분, 일본 라멘 첫 방문",
    "shoyu": "정통 라멘 스타일을 선호하는 분",
    "miso": "추운 날, 삿포로·홋카이도 여행",
    "shio": "맑은 국물·담백한 맛 선호",
    "tsukemen": "면 식감을 중시하는 분, 도쿄 츠케멘 탐방",
    "default": "여행 전 일정 잡기; 매장 공식 정보를 대신하지 않습니다",
}


def slug_to_shop_name(ramen_id: str) -> str:
    """honke_daiichi-asahi_en -> Honke Daiichi Asahi"""
    base = ramen_id.rsplit("_", 1)[0] if ramen_id.endswith(("_en", "_ko")) else ramen_id
    parts = re.split(r"[-_]+", base)
    words = []
    for p in parts:
        if not p:
            continue
        if p.isdigit():
            words.append(p)
        elif len(p) <= 3 and p.isalpha():
            words.append(p.upper())
        else:
            words.append(p.capitalize())
    return " ".join(words) if words else base


def _primary_style(categories: list) -> str:
    if not categories:
        return ""
    return str(categories[0]).strip().lower()


def _style_label(categories: list, lang: str) -> str:
    primary = _primary_style(categories)
    table = _STYLE_KO if lang == "ko" else _STYLE_EN
    return table.get(primary, str(categories[0]) if categories else "")


def _region_from_address(address: str) -> str:
    addr = (address or "").strip()
    if not addr:
        return ""
    return addr.split(",")[0].strip()


def _one_liner(post: dict, shop_name: str, lang: str) -> str:
    custom = str(post.get("one_liner") or "").strip()
    if custom:
        return custom
    summary = str(post.get("summary") or "").strip()
    if summary:
        # First sentence only, cap length
        sentence = re.split(r"(?<=[.!?])\s+", summary)[0].strip()
        if len(sentence) > 220:
            sentence = sentence[:217].rstrip() + "…"
        return sentence
    region = _region_from_address(str(post.get("address") or ""))
    style = _style_label(post.get("categories") or [], lang)
    if lang == "ko":
        return f"{region}의 {shop_name} — {style} 스타일 라멘 가게 trip-planning 가이드입니다."
    return f"{shop_name} in {region}: {style} ramen — editorial trip-planning guide (verify hours on Maps)."


def _what_to_order(categories: list, lang: str) -> str:
    primary = _primary_style(categories)
    table = _ORDER_KO if lang == "ko" else _ORDER_EN
    return table.get(primary, table["default"])


def _good_for(categories: list, lang: str) -> str:
    primary = _primary_style(categories)
    table = _GOOD_FOR_KO if lang == "ko" else _GOOD_FOR_EN
    return table.get(primary, table["default"])


def _visitor_tips(lang: str) -> list[str]:
    if lang == "ko":
        return [
            "영업 시간·휴무·가격은 방문 전 Google 지도 또는 현지 표기로 확인하세요.",
            "인기 매장은 식사 시간대 대기가 길 수 있습니다.",
            "키오스크가 있으면 현금 준비 여부를 미리 확인하세요.",
        ]
    return [
        "Confirm hours, holidays, and prices on Google Maps or at the shop before you go.",
        "Popular shops often queue at lunch and dinner — plan extra time.",
        "If there is a ticket machine, check whether cash is required.",
    ]


def apply_practical_fields(post: dict, ramen_id: str) -> None:
    """Mutate post with shop_name, h1_title, and quick-guide copy for templates."""
    lang = str(post.get("lang") or "en").lower()
    if lang not in ("en", "ko"):
        lang = "en"

    shop_name = str(post.get("shop_name") or "").strip() or slug_to_shop_name(ramen_id)
    post["shop_name"] = shop_name

    region = _region_from_address(str(post.get("address") or ""))
    style = _style_label(post.get("categories") or [], lang)

    if lang == "ko":
        h1 = str(post.get("h1_title") or "").strip() or f"{shop_name} — {region} 라멘 가이드"
        guide_heading = "빠른 방문 가이드"
        labels = {
            "style": "스타일",
            "region": "지역",
            "order": "추천 주문",
            "good_for": "이런 분께",
            "tips": "방문 전 체크",
            "background": "배경 & 상세 설명 (펼치기)",
        }
    else:
        h1 = (
            str(post.get("h1_title") or "").strip()
            or f"{shop_name} — {region} ramen guide"
        )
        guide_heading = "Quick visit guide"
        labels = {
            "style": "Style",
            "region": "Area",
            "order": "What to order",
            "good_for": "Good for",
            "tips": "Before you go",
            "background": "Background & full notes (expand)",
        }

    post["h1_title"] = h1
    post["guide_heading"] = guide_heading
    post["guide_labels"] = labels
    post["style_label"] = style
    post["region_label"] = region
    post["one_liner"] = _one_liner(post, shop_name, lang)
    post["what_to_order"] = str(post.get("what_to_order") or "").strip() or _what_to_order(
        post.get("categories") or [], lang
    )
    post["good_for"] = str(post.get("good_for") or "").strip() or _good_for(
        post.get("categories") or [], lang
    )
    post["visitor_tips"] = post.get("visitor_tips") or _visitor_tips(lang)
    if isinstance(post["visitor_tips"], str):
        post["visitor_tips"] = [t.strip() for t in post["visitor_tips"].split("\n") if t.strip()]
