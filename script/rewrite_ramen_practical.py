#!/usr/bin/env python3
"""Rewrite ramen shop markdown bodies to mid-length practical guides (EN+KO)."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from ramen_md import loads_ramen_post  # noqa: E402
from ramen_practical import slug_to_shop_name, _style_label, _region_from_address  # noqa: E402

CONTENT_DIR = ROOT / "app" / "content"

BANNED_PHRASES = (
    "Soul of the Shop",
    "Broth Analysis",
    "Noodle & Topping",
    "Best Ramen in",
    "Michelin-standard",
    "미슐랭 스타",
    "Best Ramen",
)

PROTECTED_KEYS = frozenset(
    {
        "seo_title",
        "seo_description",
        "shop_name",
        "address",
        "lat",
        "lng",
        "categories",
        "date",
        "thumbnail",
        "image_prompt",
        "agoda",
        "description",
    }
)

ALLEY_SLUGS = frozenset(
    {
        "ganso_sapporo_ramen_yokocho",
        "ganso_ramen_nagahama-ya",
        "ganso_nagahamaya",
    }
)

TSUKEMEN_HINTS = ("tsukemen", "츠케멘", "fuunji", "menya_itto", "rokurinsha", "tsujita", "ramen_nagi")

CAT_KO_TO_EN = {
    "미소": "Miso",
    "돈코츠": "Tonkotsu",
    "쇼유": "Shoyu",
    "시오": "Shio",
    "츠케멘": "Tsukemen",
    "현지인맛집": "Local Gem",
    "심야영업": "Late Night",
    "야식": "Late Night",
    "프리미엄": "Premium",
    "치킨 라멘": "Chicken",
    "비건": "Vegan-friendly",
}

CAT_EN_TO_KO = {v: k for k, v in CAT_KO_TO_EN.items()}

CHAIN_HINTS = (
    "ippudo",
    "ichiran",
    "afuri",
    "santouka",
    "tenkaippin",
    "jinrui_mina_menrui",
    "mouko_tanmen",
)

SHOP_OVERRIDES: dict[str, dict[str, dict[str, str]]] = {
    "honke_daiichi-asahi": {
        "en": {
            "hook": "Honke Daiichi Asahi (本家 第一旭) is a Kyoto Station-area shoyu ramen institution, open from very early morning. Expect a line at peak times; staff often take orders while you queue.",
            "bowl": "The bowl is a clear, shoyu-forward pork soup — not heavy Hakata tonkotsu. Thin straight noodles, generous thin-sliced chashu, and plenty of Kujo negi are typical. Extra chashu (chashu-men) is a common upgrade.",
            "visit": "Counter and table seating fill quickly. Shoulder times (very early morning or after 10 p.m.) are slightly easier. Cash and ticket-machine habits vary — check at the door.",
            "area": "Shimogyo, walking distance from Kyoto Station. Easy to pair with a station-area walk; Shinpuku Saikan is nearby if you want a second comparison bowl another day.",
        },
        "ko": {
            "hook": (
                "혼케 다이이치 아사히(本家 第一旭)는 교토역·시모교 일대에서 새벽부터 영업하는 쇼유 라멘 명가입니다. "
                "1947년부터 이어진 가게로, 교토에서 ‘맑지만 깊은’ 쇼유 라멘을 찾을 때 거론되는 곳입니다. "
                "점심·저녁에는 줄이 길 수 있고, 줄 서는 동안 주문을 받는 경우가 많습니다."
            ),
            "bowl": (
                "국물은 맑은 쇼유 돈코츠 계열로, 후쿠오카식 진한 백탕과는 결이 다릅니다. "
                "가는 직면, 얇게 썬 차슈, 쿠조 파가 기본 구성이고 차슈멘(차슈 추가)을 고르는 손님도 많습니다. "
                "첫 방문은 기본 라멘으로 국물 간을 맞춰 보는 것이 좋습니다."
            ),
            "visit": (
                "좌석 회전이 빠른 편이라 대기 시간은 생각보다 짧을 때도 있습니다. "
                "이른 아침(오픈 직후)이나 늦은 밤이 상대적으로 수월할 수 있습니다. "
                "현금·키오스크·카드 여부는 입구 안내를 확인하세요."
            ),
            "area": (
                "교토역에서 도보권 시모교입니다. 당일 교토역·우메코지 공원 동선과 묶기 좋고, "
                "다른 날 신푸쿠 사이칸 등 인근 라멘과 비교 방문하면 교토 쇼유 감이 잡힙니다."
            ),
        },
    },
    "bankara_ramen": {
        "en": {
            "hook": "Bankara Ramen in Ikebukuro is known for rich tonkotsu-shoyu bowls and late-night hours — a practical stop after evening plans in Toshima.",
            "bowl": "Signature style leans rich: pork broth with shoyu tare, noticeable fat (seabura), and kakuni-style braised pork rather than only thin chashu. Order the house tonkotsu first; spice or extra pork if you want a heavier bowl.",
            "visit": "Popular for dinner and after 9–10 p.m. Expect a short wait at peak times. Useful when other shops in the area have closed.",
            "area": "Ikebukuro is a major hub — hotels, Sunshine City, and late-night food are all nearby. Good for travelers staying north-west Tokyo.",
        },
        "ko": {
            "hook": (
                "이케부쿠로 반카라 라멘은 진한 돈코츠·쇼유와 늦은 영업으로 유명해, 토시마에서 저녁 일정 뒤 들르기 좋습니다. "
                "1998년경부터 이케부쿠로에서 이름을 알린 ‘진한 맛’ 계열 돈코츠로, 가볍게 먹기보다 든든한 한 끼에 가깝습니다."
            ),
            "bowl": (
                "국물은 돈코츠에 쇼유 다레가 얹힌 진한 편이고, 세아부라(지방)와 카쿠니(조림 돼지) 토핑이 특징입니다. "
                "기본 돈코츠로 맛본 뒤 매운맛·토핑 추가를 고려하면 됩니다. 가격은 도쿄 기준 ¥1,000~¥1,300 전후가 흔합니다."
            ),
            "visit": (
                "저녁·야간에 손님이 몰립니다. 주변 가게가 문 닫은 뒤 대안으로 찾는 경우도 많습니다. "
                "인기 시간대에는 15~25분 정도 여유를 두면 좋습니다."
            ),
            "area": (
                "이케부쿠로 역 주변 숙소·쇼핑과 연결하기 쉽습니다. "
                "도쿄 서북부 여행에서 ‘늦은 라멘 한 그릇’ 슬롯으로 넣기 좋습니다."
            ),
        },
    },
    "menya_musashi_shinjuku": {
        "en": {
            "hook": "Menya Musashi Shinjuku serves dual-broth (W-soup) tonkotsu — a Shinjuku classic for travelers who want a well-known bowl near the station.",
            "bowl": "Look for W-soup (tonkotsu + secondary broth) with firm noodles and assorted toppings. Signature bowls are on the menu board; add-ons depend on the branch.",
            "visit": "Shinjuku means crowds. Lunch and dinner queues are normal; off-peak hours or weekday lunch slightly easier.",
            "area": "Walkable from Shinjuku Station cores. Pair with an evening in Kabukicho or a daytime transfer hub stop.",
        },
        "ko": {
            "hook": "멘야 무사시 신주쿠는 쌍육수(W스프) 돈코츠로 유명한 신주쿠 대표 라멘 중 하나입니다.",
            "bowl": "돈코츠와 보조 육수를 섞은 쌍육수, 탄력 있는 면, 토핑 구성이 포인트입니다. 시그니처는 메뉴판 첫 줄을 보면 됩니다.",
            "visit": "신주쿠 특성상 점심·저녁 웨이팅이 흔합니다. 평일 점심이나 비피크가 조금 수월합니다.",
            "area": "신주쿠역 도보권입니다. 당일 신주쿠 일정 중 한 끼로 넣기 좋습니다.",
        },
    },
    "ramen_shingen": {
        "en": {
            "hook": "Ramen Shingen is a long-running Sapporo miso shop in Susukino — often queued, especially on cold evenings.",
            "bowl": "Sapporo-style miso: stir-fried miso tare, rich broth, curly noodles; butter-corn or spicy miso options are common. One bowl is usually enough for a first visit.",
            "visit": "Expect a line at dinner. Ticket machine or counter ordering — confirm on site. Winter nights are busiest.",
            "area": "Susukino nightlife district; combine with Ganso Ramen Yokocho or other Susukino stops on separate visits.",
        },
        "ko": {
            "hook": "라멘 신겐은 스스키노의 오래된 삿포로 미소 라멘으로, 추운 날 저녁에 줄이 길어지는 편입니다.",
            "bowl": "볶은 미소 다레와 진한 국물, 곱은 면이 전형적입니다. 버터·옥수수·매운 미소 옵션이 흔합니다.",
            "visit": "저녁 웨이팅을 감안하세요. 키오스크·현금 여부는 매장에서 확인합니다.",
            "area": "스스키노 한밤 동선과 잘 맞습니다. 원조 라멘 요코초와는 별도 날 비교 방문을 추천합니다.",
        },
    },
    "muteppou_kyoto": {
        "en": {
            "hook": "Muteppou Kyoto is a tonkotsu-focused shop known for intense pork broth — popular with travelers who want a rich Kyoto bowl (not light shoyu).",
            "bowl": "Heavy tonkotsu profile; noodles and kaedama (noodle refill) culture matter here. Start with the signature tonkotsu before extras.",
            "visit": "Queues at peak meal times. Small counter-focused layout. Verify hours on Maps — Kyoto shops can close on irregular days.",
            "area": "Central Kyoto access; good after temple sightseeing when you want a filling dinner.",
        },
        "ko": {
            "hook": "무테포 교토는 진한 돈코츠로 유명한 매장으로, 맑은 쇼유 계열과 다른 ‘묵직한’ 교토 라멘을 원할 때 고려합니다.",
            "bowl": "돈코츠 농도가 높은 편이며, 면 리필(가에다마) 문화가 있습니다. 시그니처 돈코츠부터 주문하는 것이 안전합니다.",
            "visit": "식사 시간대 웨이팅이 있습니다. 좌석이 카운터 중심입니다. 교토 매장은 휴무가 불규칙할 수 있어 지도로 재확인하세요.",
            "area": "관광 동선 사이 저녁 한 끼로 넣기 좋습니다.",
        },
    },
    "fuunji_shinjuku": {
        "en": {
            "hook": "Fuunji Shinjuku is a tsukemen specialist — dipping noodles in a concentrated chicken-fish broth, not a soup ramen bowl.",
            "bowl": "Order tsukemen (dipping style). Broth is served separately for dipping; ask about soup-wari (broth top-up) at the end if offered. Noodle texture is the main event.",
            "visit": "Lines are part of the experience at lunch. Eat promptly after serving — noodles firm up fast.",
            "area": "Shinjuku office/lunch crowd shop; pair with a half-day in west Shinjuku.",
        },
        "ko": {
            "hook": (
                "후운지 신주쿠는 츠케멘(찍어먹는 면) 전문점으로, 국물 라멘이 아닌 ‘육수에 찍어 먹는’ 스타일입니다. "
                "신주쿠·요요기 일대 점심 인기가 높아, ‘면 식감’을 우선할 때 짧게 들러보기 좋은 곳입니다."
            ),
            "bowl": (
                "츠케멘을 주문합니다. 면과 농축 육수가 분리 제공되며, 닭·생선 계열 육수가 진한 편입니다. "
                "마지막에 스프 와리(육수 희석)가 가능하면 남은 육수를 마실 수 있습니다."
            ),
            "visit": (
                "점심 웨이팅이 길 수 있습니다. 제공 후 빨리 먹는 것이 면 식감에 유리합니다. "
                "키오스크·현금 규칙은 입구에서 확인하세요."
            ),
            "area": (
                "신주쿠 서쪽·요요기 쪽 업무·관광 동선과 맞습니다. "
                "츠케멘은 배가 빨리 차므로 저녁 전 ‘메인 한 끼’로 계획하는 편이 좋습니다."
            ),
        },
    },
    "ganso_sapporo_ramen_yokocho": {
        "en": {
            "hook": (
                "Ganso Sapporo Ramen Yokocho (元祖さっぽろラーメン横丁) is a short covered alley in Susukino, Sapporo’s main nightlife area. "
                "The name Ganso (“original”) marks an early post-war ramen lane — a cluster of tiny counters, not one brand. "
                "You walk the passage, compare boards, and sit at whichever stall fits your queue tolerance."
            ),
            "bowl": (
                "Most stalls focus on Sapporo miso ramen: miso tare is often stir-fried before meeting pork-and-chicken broth, "
                "with thick curly noodles and toppings such as butter and sweet corn. Spicy miso (karami-miso) is common. "
                "Bowls typically run ¥900–¥1,200; sizes and toppings vary by stall."
            ),
            "visit": (
                "Seating is almost always counter-only, so expect a short wait at dinner and after 10 p.m., especially on winter weekends. "
                "There is no single house bowl — read each shop’s board, order at that stall’s machine or counter, and eat where you ordered. "
                "Hours and holidays differ per shop; use the Maps link above."
            ),
            "area": (
                "Susukino is walkable from central Sapporo stations. The alley works well after skiing or a late flight. "
                "For a broader miso comparison, pair with single-shop guides such as Ramen Shingen or Sumire Sapporo on another evening."
            ),
        },
        "ko": {
            "hook": (
                "원조 삿포로 라멘 요코초(元祖さっぽろラーメン横丁)는 스스키노 번화가 안쪽의 짧은 실내 골목입니다. "
                "‘元祖(원조)’ 이름처럼 삿포로 라멘 골목의 초기 형태를 보여 주는 장소로, 하나의 프랜차이즈가 아니라 여러 작은 가게가 붙어 있습니다. "
                "골목을 걸으며 메뉴판을 비교한 뒤 줄이 짧은 가게부터 들어가는 방식이 현실적입니다."
            ),
            "bowl": (
                "대부분 삿포로 미소 라멘입니다. 미소 다레를 웍에서 볶아 국물과 섞는 방식이 흔하고, 곱은 면에 버터·옥수수 토핑이 자주 나옵니다. "
                "매운 미소(가라미미소)도 흔합니다. 가격은 대략 ¥900~¥1,200이지만 가게마다 다릅니다."
            ),
            "visit": (
                "좌석은 카운터 위주라 저녁·주말·겨울 밤에 잠깐 대기할 수 있습니다. "
                "골목 전체가 한 메뉴가 아니므로 가게별 메뉴판을 보고 그 자리 키오스크·카운터에서 주문합니다. "
                "영업·휴무는 가게마다 다르니 상단 지도 링크로 확인하세요."
            ),
            "area": (
                "스스키노는 삿포로 역·호텔에서 도보권인 경우가 많아, 늦은 식사나 술자리 뒤 한 그릇으로 넣기 좋습니다. "
                "단일 매장 미소(라멘 신겐·스미레 등)와는 다른 날 비교하면 삿포로 미소 감을 잡기 쉽습니다."
            ),
        },
    },
}


def base_slug(stem: str) -> str:
    if stem.endswith("_en") or stem.endswith("_ko"):
        return stem.rsplit("_", 1)[0]
    return stem


def lang_from_stem(stem: str) -> str:
    if stem.endswith("_ko"):
        return "ko"
    if stem.endswith("_en"):
        return "en"
    return "en"


def detect_page_type(base: str, categories: list) -> str:
    if base in ALLEY_SLUGS:
        return "alley"
    cat = " ".join(str(c) for c in categories).lower()
    if any(h in base for h in TSUKEMEN_HINTS) or "tsukemen" in cat or "츠케멘" in cat:
        return "tsukemen"
    if any(h in base for h in CHAIN_HINTS):
        return "chain"
    return "single"


def is_late_night(categories: list) -> bool:
    joined = " ".join(str(c) for c in categories).lower()
    return "late night" in joined or "late-night" in joined or "심야" in joined or "야식" in joined


def variant_index(base: str) -> int:
    return int(hashlib.md5(base.encode()).hexdigest(), 16) % 5


def price_hint(region: str, lang: str) -> str:
    major = region in ("Tokyo", "Osaka", "Kyoto")
    if lang == "ko":
        return "대략 ¥1,000~¥1,300" if major else "대략 ¥800~¥1,100"
    return "roughly ¥1,000–¥1,300" if major else "roughly ¥800–¥1,100"


def parse_region_city(address: str) -> tuple[str, str]:
    addr = (address or "").strip()
    if not addr:
        return "", ""
    simple = [p.strip() for p in addr.split(",")]
    if (
        len(simple) >= 2
        and len(simple) <= 4
        and not re.search(r"\d{3}-\d{4}", simple[0])
        and not simple[0].lower().startswith(("2 chome", "1-", "3 ", "5-"))
    ):
        return simple[0], simple[1]

    prefs = [
        ("Hokkaido", "Sapporo"),
        ("Tokyo", "Tokyo"),
        ("Osaka", "Osaka"),
        ("Kyoto", "Kyoto"),
        ("Fukuoka", "Fukuoka"),
        ("Hiroshima", "Hiroshima"),
        ("Kanagawa", "Yokohama"),
    ]
    for region, default_city in prefs:
        if region in addr or default_city in addr:
            ward = re.search(
                r"(Shibuya|Shinjuku|Shimogyo|Chuo|Minato|Toshima|Nakagyo|Hakata|Yodogawa|Sakyo|Chiyoda|Asahikawa)\s*(City|Ward|ku)?",
                addr,
                re.I,
            )
            city = ward.group(1) if ward else default_city
            return region, city
    return simple[0], simple[1] if len(simple) > 1 else simple[0]


def normalize_categories(categories: list, lang: str) -> list:
    if not categories:
        return []
    out = []
    for c in categories:
        text = str(c).strip()
        if lang == "en" and text in CAT_KO_TO_EN:
            out.append(CAT_KO_TO_EN[text])
        elif lang == "ko" and text in CAT_EN_TO_KO:
            out.append(CAT_EN_TO_KO[text])
        else:
            out.append(text)
    return out


def merge_sibling_meta(post: dict, path: Path) -> dict:
    """Fill missing fields from the paired language file."""
    meta = dict(post.metadata)
    stem = path.stem
    lang = lang_from_stem(stem)
    sibling_lang = "ko" if lang == "en" else "en"
    sibling = CONTENT_DIR / f"{base_slug(stem)}_{sibling_lang}.md"
    if sibling.exists():
        sib = loads_ramen_post(sibling.read_text(encoding="utf-8"))
        for key in (
            "address",
            "lat",
            "lng",
            "date",
            "thumbnail",
            "image_prompt",
            "agoda",
            "shop_name",
        ):
            if not meta.get(key) and sib.get(key) is not None:
                meta[key] = sib.get(key)
        if not meta.get("categories") and sib.get("categories") is not None:
            meta["categories"] = sib.get("categories")
    if not meta.get("lang"):
        meta["lang"] = lang
    return meta


def related_slugs(base: str, lang: str, region: str, index: dict[tuple[str, str], list[str]]) -> list[str]:
    peers = [s for s in index.get((lang, region), []) if s != base]
    if not peers:
        return []
    h = int(hashlib.md5(base.encode()).hexdigest(), 16)
    out = []
    for i in range(min(2, len(peers))):
        out.append(peers[(h + i) % len(peers)])
    return out


def link_line(lang: str, slugs: list[str]) -> str:
    if not slugs:
        return ""
    parts = []
    for s in slugs:
        name = slug_to_shop_name(f"{s}_{lang}")
        parts.append(f"[{name}](/ramen/{s}_{lang})")
    if lang == "ko":
        return " 같은 지역 다른 가게: " + ", ".join(parts) + "."
    return " More in the area: " + ", ".join(parts) + "."


def build_title(shop_name: str, region: str, style: str, lang: str, page_type: str) -> str:
    if lang == "ko":
        if page_type == "alley":
            return f"{shop_name} — {region} 라멘 골목 가이드"
        return f"{shop_name} — {region} {style} 라멘 가이드"
    if page_type == "alley":
        return f"{shop_name} — {region} ramen alley guide"
    return f"{shop_name} — {region} {style} ramen guide"


def build_summary(shop_name: str, region: str, style: str, lang: str, page_type: str) -> str:
    if lang == "ko":
        if page_type == "alley":
            return (
                f"{region} {shop_name}는 여러 작은 가게가 모인 라멘 골목입니다. "
                f"가게마다 영업시간과 메뉴가 다르니 방문 전 지도로 확인하세요."
            )
        if page_type == "tsukemen":
            return (
                f"{region} {shop_name} 츠케멘 가이드 — 면과 육수를 분리해 먹는 스타일, "
                f"웨이팅·주문 요령을 정리했습니다. 영업시간은 지도에서 재확인하세요."
            )
        return (
            f"{region} {shop_name} — {style} 라멘. 웨이팅·주문·추천 메뉴를 "
            f"여행 전에 확인할 수 있는 실용 가이드입니다."
        )
    if page_type == "alley":
        return (
            f"{shop_name} is a walkable ramen alley in {region} with many small counters — "
            f"each shop sets its own menu and hours. Check Google Maps before you go."
        )
    if page_type == "tsukemen":
        return (
            f"{shop_name} in {region}: tsukemen (dipping noodles) — practical notes on queues, "
            f"ordering, and how to eat the bowl. Verify hours on Maps."
        )
    return (
        f"{shop_name} in {region}: {style} ramen — practical guide to queues, ordering, "
        f"and what to try. Confirm hours on Google Maps before visiting."
    )


def build_one_liner(
    shop_name: str, region: str, city: str, style: str, lang: str, page_type: str, late: bool
) -> str:
    if lang == "ko":
        tail = "늦은 시간 영업 가능 — 지도로 시간 확인." if late else "방문 전 지도에서 영업·휴무 확인."
        if page_type == "alley":
            loc = f"{region} {city}".strip()
            return f"{loc} 라멘 골목 — 작은 가게 여러 곳을 한 번에 비교하기 좋음. {tail}"
        if page_type == "tsukemen":
            return f"{region} 츠케멘 전문 — 면과 육수를 따로 받아 찍어 먹는 스타일. {tail}"
        return f"{region} {style} 라멘 — {shop_name}. {tail}"
    tail = "Late-night hours possible — confirm on Maps." if late else "Verify hours and holidays on Maps before you go."
    if page_type == "alley":
        return f"A lane of small ramen counters in {region} — good for comparing bowls in one walk. {tail}"
    if page_type == "tsukemen":
        return f"Tsukemen specialist in {region}: noodles and broth served separately. {tail}"
    return f"{style} ramen at {shop_name}, {region}. {tail}"


def build_what_to_order(style: str, lang: str, page_type: str, override: dict | None) -> str:
    if override and override.get("order"):
        return override["order"]
    if page_type == "tsukemen":
        return "츠케멘(기본) — 가능하면 마지막에 스프 와리" if lang == "ko" else "House tsukemen; ask about soup-wari (broth top-up) if offered."
    if page_type == "alley":
        return "가게 기본 미소/쇼유 라멘 — 메뉴판 첫 번째 인기 메뉴" if lang == "ko" else "Each stall’s signature miso or shoyu bowl — start with the menu board’s top item."
    orders_en = {
        "miso": "House miso ramen; butter-corn or spicy miso if you want Sapporo-style toppings.",
        "tonkotsu": "Signature tonkotsu ramen; extra chashu or kaedama if you want a heavier bowl.",
        "shoyu": "Classic shoyu ramen — taste the broth before adding condiments.",
        "shio": "Shio (salt) ramen for a lighter, clearer broth.",
        "tsukemen": "Tsukemen set; finish with soup-wari if available.",
    }
    orders_ko = {
        "미소": "기본 미소 라멘 — 버터·옥수수·매운맛 옵션 확인",
        "돈코츠": "시그니처 돈코츠 — 차슈·면 추가(가에다마)는 매장 규칙 확인",
        "쇼유": "기본 쇼유 라멘 — 국물 맛 본 뒤 조미료 추가",
        "시오": "시오(소금) 라멘 — 맑은 국물 선호 시",
        "츠케멘": "츠케멘 세트 — 스프 와리 가능 여부 확인",
    }
    key = style.lower()
    if lang == "ko":
        return orders_ko.get(key, "메뉴판 시그니처 라멘 — 키오스크가 어렵다면 직원에게 문의")
    return orders_en.get(key, "The shop’s signature bowl on the menu board.")


def build_good_for(style: str, lang: str, page_type: str, late: bool) -> str:
    if lang == "ko":
        bits = []
        if page_type == "alley":
            bits.append("한 골목에서 여러 가게 비교")
        if page_type == "tsukemen":
            bits.append("면 식감·츠케멘 입문")
        if late:
            bits.append("늦은 시간 한 끼")
        if style in ("미소", "Miso"):
            bits.append("추운 날 든든한 한 그릇")
        if not bits:
            bits.append("여행 전 일정 잡기")
        return ", ".join(bits)
    bits = []
    if page_type == "alley":
        bits.append("Comparing several stalls in one visit")
    if page_type == "tsukemen":
        bits.append("Tsukemen fans and noodle-texture seekers")
    if late:
        bits.append("Late-night meals")
    if style.lower() == "miso":
        bits.append("Cold-weather comfort bowls")
    if not bits:
        bits.append("Trip planning before you land")
    return ", ".join(bits)


def style_detail(lang: str, style: str, region: str) -> str:
    s = style.lower()
    if lang == "ko":
        table = {
            "미소": (
                f"{region} 미소 라멘은 지역마다 농도가 다릅니다. 삿포로·홋카이도는 볶은 미소 다레와 "
                f"버터·옥수수 토핑이 흔하고, 도쿄보다 진한 편인 경우가 많습니다."
            ),
            "돈코츠": (
                "돈코츠는 돼지뼈 우려낸 국물이 중심입니다. 후쿠오카는 맑고 진한 백탕, "
                "도쿄는 쇼유·간장과 섞이거나 지방맛(세아부라)이 강한 메뉴가 많습니다."
            ),
            "쇼유": (
                "쇼유 라멘은 간장 다레와 육수의 균형이 핵심입니다. 교토·도쿄는 상대적으로 맑은 편, "
                "지역 물과 간장 블렌드에 따라 짠맛·감칠맛이 달라집니다."
            ),
            "시오": (
                "시오(소금) 라멘은 맑고 가벼운 국물이 특징입니다. 해산물 육수를 쓰는 지역(예: 함관)과 "
                "닭·돼지 육수를 쓰는 지역 모두 있습니다."
            ),
            "츠케멘": (
                "츠케멘은 면과 육수가 분리됩니다. 육수 농도가 높아 찍어 먹고, 마지막에 스프 와리로 "
                "마실 수 있는 매장이 많습니다."
            ),
        }
        return table.get(s, f"{style} 스타일은 매장마다 육수 농도와 면 굵기가 다릅니다. 메뉴판 설명을 먼저 보세요.")
    table = {
        "miso": (
            f"{region} miso ramen varies by city — Sapporo/Hokkaido styles often use stir-fried miso tare "
            f"and butter-corn toppings; Tokyo versions can be lighter."
        ),
        "tonkotsu": (
            "Tonkotsu means pork-bone broth. Hakata styles are milky and dense; Tokyo bowls may mix shoyu "
            "or add heavier seabura (fat back)."
        ),
        "shoyu": (
            "Shoyu ramen is about soy tare plus broth balance. Kyoto/Tokyo bowls often look clearer than tonkotsu; "
            "saltiness depends on local soy blend."
        ),
        "shio": (
            "Shio (salt) ramen keeps a lighter, clearer soup — good when you want clarity over richness. "
            "Some regions lean seafood-forward broths."
        ),
        "tsukemen": (
            "Tsukemen serves noodles and broth separately. The dip is concentrated; soup-wari at the end "
            "dilutes leftovers into a drinkable soup."
        ),
    }
    return table.get(
        s,
        f"{style} style differs shop by shop in noodle cut and broth weight — read the board before ordering.",
    )


def section_labels(lang: str, variant: int, page_type: str) -> tuple[str, str, str, str, str]:
    idx = variant % 4
    if lang == "ko":
        sets = [
            ("이 가게 한줄", "메뉴·국물", "웨이팅·주문", "주변 동선", "스타일 참고"),
            ("소개", "실전 팁", "대기·영업", "함께 가기 좋은 곳", "메모"),
            ("한 그릇 요약", "방문 전 체크", "지역", "주문", "스타일"),
            ("특징", "국물·면", "웨이팅", "주변", "참고"),
        ]
        if page_type == "tsukemen":
            sets = [
                ("츠케멘 기본", "먹는 순서", "웨이팅·주문", "주변", "스타일 참고"),
                ("소개", "찍어먹기 팁", "대기", "동선", "메모"),
                ("한 그릇", "면 식감", "영업", "주변", "참고"),
                ("특징", "육수", "웨이팅", "지역", "메모"),
            ]
        if page_type == "alley":
            sets = [
                ("골목 소개", "가게 고르기", "웨이팅·주문", "주변", "스타일 참고"),
                ("구조", "비교 팁", "영업", "동선", "메모"),
                ("한눈에", "스톨 선택", "대기", "주변", "참고"),
                ("소개", "메뉴", "실전", "지역", "메모"),
            ]
        return sets[idx]
    sets = [
        ("Overview", "The bowl", "Queue & ordering", "Area", "Style note"),
        ("What to expect", "Practical notes", "Wait & hours", "Nearby", "Extra"),
        ("At a glance", "Menu", "Before you go", "Getting there", "Reference"),
        ("Intro", "Broth & noodles", "Queues", "Around", "Tip"),
    ]
    if page_type == "tsukemen":
        sets = [
            ("Overview", "How to eat", "Queue & hours", "Area", "Style note"),
            ("Basics", "Dipping tips", "Ordering", "Nearby", "Extra"),
            ("At a glance", "Noodles", "Wait", "Around", "Reference"),
            ("Intro", "Broth", "Practical", "Area", "Tip"),
        ]
    if page_type == "alley":
        sets = [
            ("Overview", "How the alley works", "Picking a stall", "Area", "Style note"),
            ("Basics", "Comparing stalls", "Queues", "Nearby", "Extra"),
            ("At a glance", "Menus", "Practical", "Around", "Reference"),
            ("Intro", "What to eat", "Ordering", "Area", "Tip"),
        ]
    return sets[idx]


def paragraph(label: str, text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if label:
        return f"**{label}:** {text}"
    return text


def maps_footer(lang: str, shop_name: str) -> str:
    if lang == "ko":
        return (
            f"마지막으로, {shop_name}의 휴무·라스트오더·임시 휴점은 계절마다 바뀝니다. "
            f"와이파이가 있는 곳에서 지도 정보를 캡처해 두고, 문이 닫혀 있으면 같은 지역·비슷한 스타일 가게를 "
            f"도보권에서 찾는 편이 현실적입니다. 이 가이드는 예약·보장이 아닌 trip-planning 참고용입니다."
        )
    return (
        f"Finally, holidays, seasonal closures, and last-order times change. "
        f"Screenshot the Maps listing while you have data; if {shop_name} is closed, "
        f"search the same style within walking distance rather than treating this page as a booking. "
        f"Editorial trip-planning only — not a reservation."
    )


def local_tip(lang: str, base: str, late: bool) -> str:
    h = int(hashlib.md5((base + lang).encode()).hexdigest(), 16) % 4
    if lang == "ko":
        tips = [
            "비 피크 시간(오픈 직후·늦은 저녁)을 노리면 웨이팅이 줄어드는 경우가 많습니다.",
            "키오스크가 일본어만일 때는 메뉴 사진·가격(¥) 숫자만으로도 대략 고를 수 있습니다.",
            "첫 그릇은 기본 사이즈로, 두 번째 방문 때 토핑·면 추가를 시도하는 편이 낭비가 적습니다.",
            "지역 상권이 작으면 월요일·연휴 다음 날 휴무가 잦으니 지도 휴무일을 꼭 봅니다.",
        ]
        if late:
            tips[h] += " 심야 영업 매장은 22시 이후가 상대적으로 한산한 경우도 있습니다."
        return tips[h]
    tips = [
        "Off-peak slots (just after opening or late evening) often shorten queues.",
        "Japanese-only ticket screens still work if you follow photos and ¥ prices.",
        "Start with a regular size; save extra chashu or kaedama for a second visit.",
        "Small shops often close Mondays or the day after holidays — check Maps rest days.",
    ]
    if late:
        tips[h] += " Late-night branches can be quieter after 10 p.m."
    return tips[h]


def generate_body(
    *,
    base: str,
    lang: str,
    shop_name: str,
    region: str,
    city: str,
    style: str,
    page_type: str,
    late: bool,
    related: list[str],
    override: dict | None,
) -> str:
    v = variant_index(base)
    l1, l2, l3, l4, l5 = section_labels(lang, v, page_type)
    price = price_hint(region, lang)
    links = link_line(lang, related)
    p5 = style_detail(lang, style, region)

    if override:
        p1 = override.get("hook", "")
        p2 = override.get("bowl", "")
        p3 = override.get("visit", "")
        p4 = override.get("area", "") + links
        p6 = local_tip(lang, base, late)
        p7 = maps_footer(lang, shop_name)
        parts = [
            paragraph(l1, p1),
            paragraph(l2, p2),
            paragraph(l3, p3),
            paragraph(l4, p4),
            paragraph(l5, p5),
            paragraph("", p6),
            paragraph("", p7),
        ]
        return "\n\n".join(p for p in parts if p.strip())

    if lang == "ko":
        if page_type == "alley":
            p1 = (
                f"{shop_name}은(는) {region} {city} 일대의 좁은 라멘 골목입니다. "
                f"하나의 브랜드가 아니라 여러 작은 가게가 나란히 있으며, 가게마다 메뉴·영업시간·주문 방식이 다릅니다. "
                f"‘이름만 보고 한 가게를 고르기’보다 골목 전체를 비교 방문하는 목적에 가깝습니다."
            )
            p2 = (
                f"대부분 {style} 스타일 라멘이 중심입니다. 골목을 걸으며 메뉴판·사진·줄 길이를 비교한 뒤, "
                f"첫 방문은 기본 라멘 한 그릇으로 시작하는 것이 좋습니다. 가격은 {price} 수준이 많고, "
                f"토핑·사이즈 업은 가게마다 다릅니다."
            )
            p3 = (
                f"좌석은 카운터 위주라 저녁·주말·겨울 밤에 잠깐 대기할 수 있습니다. "
                f"각 가게 키오스크·현금·카드 규칙이 달라 입구 안내를 확인하세요. "
                f"영업·휴무는 골목 공통이 아니라 가게별이므로 상단 지도 링크로 ‘그 가게’ 시간을 봐야 합니다."
            )
            p4 = (
                f"{city} 번화가·숙소에서 도보권인 경우가 많아, 당일 늦은 식사나 이틀에 걸쳐 두 스톨을 비교하기 좋습니다. "
                f"한 골목에서 두 그릇 이상 먹을 계획이면 면 양이 큰 편인지 메뉴판에서 먼저 확인하세요.{links}"
            )
        elif page_type == "tsukemen":
            p1 = (
                f"{region} {shop_name}은(는) 국물에 면을 담가 먹는 츠케멘 전문점입니다. "
                f"라멘 한 그릇처럼 국물을 먼저 마시는 방식이 아니라, 농축 육수에 면을 찍어 먹습니다. "
                f"면이 식기 전에 제공되므로 테이블에 앉자마자 시작하는 것이 좋습니다."
            )
            p2 = (
                f"면 식감과 육수 농도가 핵심입니다. 기본 츠케멘으로 시작하고, 매장에서 스프 와리(육수 희석)를 제공하면 "
                f"마지막에 남은 육수를 마실 수 있습니다. 가격대는 보통 {price}이며, 면 추가(가에다마) 규칙은 매장마다 다릅니다."
            )
            p3 = (
                f"점심 시간대 웨이팅이 길 수 있습니다. 제공 후 면이 불어나기 전에 빨리 먹는 것이 좋습니다. "
                f"인기 매장은 현금·키오스크 규칙이 있으니 문 앞 안내를 확인하세요. "
                f"{'늦은 시간 영업이 있는 날은 상대적으로 한산할 수 있습니다. ' if late else ''}"
            )
            p4 = f"{city} 역·오피스 거리와 묶어 점심이나 늦은 저녁 한 끼로 넣기 좋습니다. 츠케멘은 배가 금방 차므로 관광 일정 중간 ‘가벼운 메인’으로 계획하세요.{links}"
        elif page_type == "chain":
            p1 = (
                f"{shop_name}은(는) {region} {city}에 있는 체인·분점 성격의 라멘 가게입니다. "
                f"본점·다른 도시 지점과 메뉴·영업시간·키오스크 방식이 다를 수 있으니 ‘이 지점’ 기준으로 지도에서 확인하세요. "
                f"브랜드 이름만 보고 예상하면 실제와 다른 경우가 있습니다."
            )
            p2 = (
                f"대표 스타일은 {style}입니다. 메뉴판에서 시그니처(店のおすすめ)를 고르면 실패 확률이 낮습니다. "
                f"토핑·사이즈 업은 키오스크 화면에서 선택하는 경우가 많고, 가격은 {price} 전후가 흔합니다."
            )
            p3 = (
                f"유명 브랜드는 식사 시간대 대기가 있습니다. 줄이 길면 근처 다른 지점을 검색해 보는 것도 방법입니다. "
                f"{'이 지점은 심야·늦은 영업이 강점일 수 있습니다. ' if late else ''}"
                f"일본 현지에서는 회전이 빠른 편이라도, 첫 방문은 30분 여유를 두면 스트레스가 적습니다."
            )
            p4 = f"{city} 여행 동선 중 한 끼로 넣기 쉬운 위치인지 지도로 확인하세요. 체인이라도 ‘이번 여행에서 한 번’ 목적이라면 영업·무만 맞으면 충분합니다.{links}"
        else:
            p1 = (
                f"{region} {city}의 {shop_name}은(는) {style} 라멘을 중심으로 하는 가게입니다. "
                f"현지에서 ‘한 그릇’ 목적지로 찾기 전, 영업시간과 웨이팅 패턴을 짚어 두면 일정이 수월합니다. "
                f"이 페이지는 공식 홈페이지를 대신하지 않으니, 방문 당일 지도에서 최신 정보를 다시 확인하세요."
            )
            p2 = (
                f"첫 방문은 시그니처 메뉴(기본 라멘)가 안전합니다. 국물이 진한 편이면 토핑 추가는 나중에 고려해도 됩니다. "
                f"가격은 대체로 {price} 전후이며, 현금 전용·식권 자동판매기가 있는 매장도 많습니다."
            )
            p3 = (
                f"인기 시간대(점심 12~13시, 저녁 18~20시)에는 10~30분 대기가 나올 수 있습니다. "
                f"{'심야 영업이 강점이라 늦은 시간이 상대적으로 한산할 수 있습니다. ' if late else ''}"
                f"키오스크가 있으면 현금 필요 여부를 미리 확인하고, 일본어 메뉴는 사진·한자 키워드(라멘·차슈·미소)로 대략 파악할 수 있습니다."
            )
            p4 = (
                f"주변 지역 산책·다음 식사 계획과 연결해 보세요. "
                f"같은 {region} 안에서 스타일이 다른 가게를 하루 간격으로 비교하면 입맛에 맞는 쪽을 찾기 쉽습니다.{links}"
            )
    else:
        if page_type == "alley":
            p1 = (
                f"{shop_name} is a narrow ramen lane in {city}, {region} — not one restaurant but many small counters side by side. "
                f"Each stall sets its own menu, prices, and hours. Treat it as a sampler walk, not a single branded shop."
            )
            p2 = (
                f"Most stalls lean {style.lower()}. Walk the alley, compare boards and queues, and start with a basic bowl at whichever stall looks reasonable. "
                f"Typical prices run {price}; toppings and sizes vary by stall."
            )
            p3 = (
                f"Seating is mostly counter-only, so short waits appear at dinner and on weekends. "
                f"Ticket, cash, and card rules differ per stall — check at the door. "
                f"Hours are per shop, not lane-wide; use the Maps link above for the specific pin you choose."
            )
            p4 = (
                f"Often walkable from hotels and nightlife in {city}; good for a late bowl or comparing two stalls on separate nights. "
                f"If you plan two bowls in one evening, check noodle portion size on each board first.{links}"
            )
        elif page_type == "tsukemen":
            p1 = (
                f"{shop_name} in {city}, {region} is a tsukemen shop — you dip noodles into a separate concentrated broth, not a standard soup ramen bowl. "
                f"Noodles are served ready to dip; start soon after they arrive."
            )
            p2 = (
                f"Texture is the main event. Order the house tsukemen first; if soup-wari is offered, you can dilute leftover broth and drink it at the end. "
                f"Budget around {price}; kaedama (extra noodles) rules vary."
            )
            p3 = (
                f"Lunch queues are common. Eat promptly so noodles stay firm. "
                f"Confirm cash vs ticket machine at the entrance. "
                f"{'Late service can be quieter on some days. ' if late else ''}"
            )
            p4 = (
                f"Works as a focused meal in {city} between sightseeing blocks. "
                f"Tsukemen fills you quickly — plan it as a main meal, not a light snack before dinner.{links}"
            )
        elif page_type == "chain":
            p1 = (
                f"{shop_name} is a chain or franchise branch in {city}, {region}. Menus and hours can differ from other branches — verify this location on Maps. "
                f"Do not assume the Tokyo main shop menu matches this pin."
            )
            p2 = (
                f"Primary style: {style.lower()}. Pick the signature item on the board first; upgrades are usually on the ticket screen. "
                f"Budget around {price} for a standard bowl."
            )
            p3 = (
                f"Expect queues at lunch and dinner. If the line is long, search for another branch nearby. "
                f"{'Late-night hours are a plus at this branch. ' if late else ''}"
                f"Even fast-turnover shops deserve 20–30 minutes of buffer on a first visit."
            )
            p4 = (
                f"Drop it into a {city} day when you want a reliable, well-known bowl. "
                f"For a one-time trip, matching open hours matters more than finding a ‘perfect’ branch.{links}"
            )
        else:
            p1 = (
                f"{shop_name} is a {style.lower()} ramen shop in {city}, {region}. "
                f"Use this page for trip planning — always confirm today's hours on Google Maps. "
                f"This is editorial guidance, not the shop's official site."
            )
            p2 = (
                f"First visit: order the signature bowl on the menu. Add extra chashu or noodles only if you want a heavier meal. "
                f"Prices are typically {price}; many shops use ticket machines (cash only in some cases)."
            )
            p3 = (
                f"Plan extra time at lunch (12:00–13:00) and dinner (18:00–20:00). "
                f"{'Late-night hours help when other kitchens have closed. ' if late else ''}"
                f"Read the ticket screen photos if the menu is Japanese-only — look for ramen, chashu, miso, shoyu keywords."
            )
            p4 = (
                f"Pair with other {region} stops the same day or compare two styles on separate days. "
                f"On-site signage and Maps beat any third-party summary for holidays and last order times.{links}"
            )

    p6 = local_tip(lang, base, late)
    p7 = maps_footer(lang, shop_name)
    parts = [
        paragraph(l1, p1),
        paragraph(l2, p2),
        paragraph(l3, p3),
        paragraph(l4, p4),
        paragraph(l5, p5),
        paragraph("", p6),
        paragraph("", p7),
    ]
    return "\n\n".join(p for p in parts if p.strip())


def dump_frontmatter(meta: dict) -> str:
    """Serialize metadata as YAML (stable, no JSON block)."""

    def represent_str(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        if any(c in data for c in ":{}[]#&*!|>'\"%@`"):
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    class Dumper(yaml.SafeDumper):
        pass

    Dumper.add_representer(str, represent_str)

    ordered: dict = {}
    priority = [
        "address",
        "agoda",
        "categories",
        "date",
        "image_prompt",
        "lang",
        "lat",
        "lng",
        "shop_name",
        "summary",
        "thumbnail",
        "title",
        "one_liner",
        "what_to_order",
        "good_for",
        "seo_title",
        "seo_description",
        "description",
    ]
    for k in priority:
        if k in meta and meta[k] is not None and meta[k] != "":
            ordered[k] = meta[k]
    for k, v in meta.items():
        if k not in ordered and v is not None and v != "":
            ordered[k] = v
    return yaml.dump(ordered, Dumper=Dumper, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()


def rewrite_file(path: Path, region_index: dict[tuple[str, str], list[str]], dry_run: bool = False) -> bool:
    raw = path.read_text(encoding="utf-8")
    post = loads_ramen_post(raw)
    meta = merge_sibling_meta(post, path)

    stem = path.stem
    base = base_slug(stem)
    lang = lang_from_stem(stem)
    if not meta.get("lang"):
        meta["lang"] = lang

    shop_name = str(meta.get("shop_name") or "").strip() or slug_to_shop_name(stem)
    meta["shop_name"] = shop_name
    meta["categories"] = normalize_categories(meta.get("categories") or [], lang)
    region, city = parse_region_city(str(meta.get("address") or ""))
    style = _style_label(meta.get("categories") or [], lang)
    page_type = detect_page_type(base, meta.get("categories") or [])
    late = is_late_night(meta.get("categories") or [])
    override_pack = SHOP_OVERRIDES.get(base, {}).get(lang)
    related = related_slugs(base, lang, region, region_index)

    meta["title"] = build_title(shop_name, region, style, lang, page_type)
    meta["summary"] = build_summary(shop_name, region, style, lang, page_type)
    meta["one_liner"] = build_one_liner(shop_name, region, city or region, style, lang, page_type, late)
    meta["what_to_order"] = build_what_to_order(style, lang, page_type, override_pack)
    meta["good_for"] = build_good_for(style, lang, page_type, late)

    body = generate_body(
        base=base,
        lang=lang,
        shop_name=shop_name,
        region=region,
        city=city or region,
        style=style,
        page_type=page_type,
        late=late,
        related=related,
        override=override_pack,
    )

    for phrase in BANNED_PHRASES:
        if phrase in body or phrase in meta.get("title", "") or phrase in meta.get("summary", ""):
            raise ValueError(f"{path.name}: banned phrase {phrase!r}")

    new_text = f"---\n{dump_frontmatter(meta)}\n---\n\n{body}\n"
    if dry_run:
        return True
    path.write_text(new_text, encoding="utf-8")
    return True


def build_region_index() -> dict[tuple[str, str], list[str]]:
    idx: dict[tuple[str, str], list[str]] = {}
    for p in CONTENT_DIR.glob("*.md"):
        post = loads_ramen_post(p.read_text(encoding="utf-8"))
        meta = merge_sibling_meta(post, p)
        base = base_slug(p.stem)
        lang = lang_from_stem(p.stem)
        region = _region_from_address(str(meta.get("address") or ""))
        if region:
            idx.setdefault((lang, region), []).append(base)
    for k in idx:
        idx[k] = sorted(set(idx[k]))
    return idx


def needs_practical_rewrite(path: Path) -> bool:
    """True if file still uses the old template or lacks practical frontmatter."""
    text = path.read_text(encoding="utf-8")
    if any(phrase in text for phrase in BANNED_PHRASES):
        return True
    post = loads_ramen_post(text)
    if not str(post.get("one_liner") or "").strip():
        return True
    return False


def main() -> None:
    dry = "--dry-run" in sys.argv
    template_only = "--template-only" in sys.argv
    region_index = build_region_index()
    ok = 0
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if template_only and not needs_practical_rewrite(path):
            continue
        rewrite_file(path, region_index, dry_run=dry)
        ok += 1
    label = "template " if template_only else ""
    print(f"Rewrote {ok} {label}ramen files{' (dry-run)' if dry else ''}")


if __name__ == "__main__":
    main()
