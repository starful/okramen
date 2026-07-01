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
            "order": "Classic shoyu ramen first; chashu-men if you want extra pork. Taste the broth before adding condiments.",
            "hook": (
                "Honke Daiichi Asahi (本家 第一旭) is a Kyoto Station-area shoyu ramen shop that has operated since 1947. "
                "It opens very early — often before 6 a.m. — which makes it useful after a Shinkansen arrival or before temple sightseeing. "
                "The shop is not a tiny counter-only hole-in-the-wall; expect a mix of counter and table seats, but lines still form at lunch and dinner. "
                "Staff sometimes take orders while you queue, which speeds turnover once you sit down."
            ),
            "bowl": (
                "The signature bowl is a clear, shoyu-forward pork soup — lighter than Hakata tonkotsu but still savory. "
                "Thin straight noodles, a pile of Kujo negi (Kyoto scallions), and thin-sliced chashu are standard. "
                "Many regulars order chashu-men for extra pork. Bowls typically run roughly ¥900–¥1,100; sizes and toppings are on the ticket screen or menu board. "
                "First visit: order the basic shoyu, sip the broth before adding table condiments, then decide if you want a heavier bowl next time."
            ),
            "visit": (
                "Peak queues happen 11:30 a.m.–2 p.m. and 6–8 p.m. Early morning (right after opening) or late evening is usually calmer. "
                "Turnover is fast — most diners finish in 15–20 minutes. Payment may be ticket machine or counter; cash-only days still happen in Kyoto, so check signage at the entrance. "
                "There is no reservation system. If the line looks long, screenshot the Maps listing and compare nearby shoyu shops rather than waiting without a plan."
            ),
            "area": (
                "Located in Shimogyo, walking distance from Kyoto Station’s central exit area and Umekoji Park. "
                "Works well as a first meal in Kyoto or a late bowl after a day in Fushimi or Arashiyama (train back to Kyoto Station). "
                "For a second comparison bowl on another day, Shinpuku Saikan and other station-area shoyu shops are nearby — Kyoto shoyu is about clarity and soy balance, not richness alone."
            ),
        },
        "ko": {
            "order": "기본 쇼유 라멘 — 국물 맛 본 뒤 차슈멘·토핑 추가 고려",
            "hook": (
                "혼케 다이이치 아사히(本家 第一旭)는 1947년부터 이어진 교토역·시모교 일대 쇼유 라멘 가게입니다. "
                "새벽 6시 전후 오픈이라 신칸센 도착 직후·관광 전 아침 한 끼로 쓰기 좋습니다. "
                "카운터와 테이블 좌석이 있지만 점심·저녁에는 줄이 생깁니다. "
                "줄을 서는 동안 주문을 받는 경우가 있어, 착석 후 대기 시간이 짧게 느껴지기도 합니다. "
                "교토에서 ‘역 근처 쇼유’를 찾을 때 자주 거론되며, 맑은 국물·파 토핑이 인상적인 편입니다."
            ),
            "bowl": (
                "맑은 쇼유 돈코츠 계열 국물로, 후쿠오카식 진한 백탕과는 결이 다릅니다. "
                "가는 직면, 쿠조 파(교토 품종 파), 얇게 썬 차슈가 기본입니다. "
                "차슈멘(차슈 추가)을 고르는 손님이 많고, 가격은 대략 ¥900~¥1,100 전후가 흔합니다. "
                "첫 방문은 기본 쇼유로 국물 간을 확인한 뒤, 테이블 조미료는 국물 맛 본 다음 넣는 편이 좋습니다. "
                "국물 표면의 기름막은 감칠맛의 일부이니, 너무 걷어내지 않고 한 모금 맛본 뒤 조절하세요."
            ),
            "visit": (
                "11:30~14:00, 18:00~20:00 전후가 가장 붐빕니다. 오픈 직후·21시 이후가 상대적으로 수월할 수 있습니다. "
                "회전이 빨라 15~20분 내 식사를 마치는 손님이 많습니다. "
                "식권기·현금 전용·카드 가능 여부는 입구 안내를 확인하세요. 예약은 없습니다. "
                "줄이 길어도 주문·착석이 빠른 편이라, ‘30분 이상’ 안내가 없다면 기다릴 가치가 있는 경우가 많습니다. "
                "테이블석이 있어도 혼자 방문 시 카운터에 앉히는 경우가 흔합니다."
            ),
            "area": (
                "교토역 중앙 출구·우메코지 공원에서 도보권입니다. "
                "교토 첫날 아침이나 후시미·아라시야마 일정 후 역으로 돌아올 때 한 끼로 넣기 좋습니다. "
                "다른 날 신푸쿠 사이칸 등 역 주변 쇼유 라멘과 비교하면 교토 쇼유의 ‘맑고 짠맛’ 감을 잡기 쉽습니다. "
                "역 주변 숙소에서 ‘아침 라멘’ 일정으로 넣기 쉬워, 신칸센 도착 당일·출발 전날 모두 후보가 됩니다."
            ),
            "extra": (
                "교토 쇼유 라멘은 ‘진한 돈코츠’를 기대하고 오면 실망할 수 있습니다 — 맑고 짠맛·파 향이 중심입니다. "
                "테이블의 마늘·고추 기름·식초는 국물 한 모금 마신 뒤 넣는 편이 좋습니다. "
                "가방은 발밑이나 등 뒤 좁은 공간에 두고, 카운터에서는 이웃과 팔꿈치 간격을 조금만 신경 쓰면 됩니다. "
                "교토역 주변은 호텔·숙소가 많아 아침 일찍 줄이 길어도 20~30분 내에 들어가는 경우가 많습니다. "
                "신칸센 도착 직후라면 캐리어를 역 코인로커에 맡기고 가볍게 들르는 동선이 편합니다. "
                "차슈멘은 고기 양이 늘지만 국물량은 비슷한 경우가 많아, ‘면까지’ 든든히 먹고 싶을 때 고르세요. "
                "교토는 관광지라 현금만 받는 날이 가끔 있으니, 입구 스티커와 지도 리뷰의 최근 댓글도 함께 확인하면 좋습니다."
            ),
            "extra2": (
                "혼자 여행이라면 카운터석이 회전이 빠르고 대기 시간을 줄이기 쉽습니다. "
                "교토역에서 도보 10~15분이면 충분한 경우가 많지만, Google Maps ‘대중교통’이 아닌 ‘도보’ 경로로 확인하세요. "
                "비·눈 오는 날에도 줄이 줄지 않는 편이라, 우산 접어두기 공간이 있는지 입구에서 가볍게 확인하면 좋습니다. "
                "교토 패스만으로는 접근이 애매할 수 있어, ‘교토역’ 기준 도보 동선으로 계획하는 편이 실수가 적습니다."
            ),
        },
    },
    "bankara_ramen": {
        "en": {
            "order": "House tonkotsu or bankara-style bowl first; add spice or extra pork if you want heavier.",
            "hook": (
                "Bankara Ramen in Ikebukuro (Toshima) is known for rich tonkotsu-shoyu bowls and hours that stretch into the night — "
                "useful when other Tokyo shops have closed. The brand started in Ikebukuro in the late 1990s and leans toward "
                "‘heavy’ rather than light: visible pork fat, dark shoyu tare, and kakuni-style braised pork cubes rather than thin chashu only."
            ),
            "bowl": (
                "Signature bowls combine pork bone broth with shoyu seasoning and seabura (back fat). "
                "Kakuni toppings are a brand signature — thicker, braised pork compared with standard chashu slices. "
                "Spicy versions and extra pork upgrades are common on the menu board. Expect roughly ¥1,000–¥1,300 in central Tokyo. "
                "First visit: order the house tonkotsu or the shop’s named ‘bankara’ bowl before experimenting with spice levels."
            ),
            "visit": (
                "Dinner (7–10 p.m.) and late-night slots draw office workers and travelers. Waits of 15–25 minutes happen at peak but move steadily. "
                "Counter seating dominates; groups may wait longer for adjacent seats. Ticket machines are common — follow photos and ¥ prices if the screen is Japanese-only. "
                "Confirm last order on Maps; Ikebukuro branches often stay open later than suburban shops."
            ),
            "area": (
                "Ikebukuro Station is a major hub on the Yamanote Line — Sunshine City, hotels, and late-night konbini are all nearby. "
                "Good for northwest Tokyo stays or after an evening in Ikebukuro’s entertainment district. "
                "If Bankara’s line is too long, search ‘tonkotsu’ within walking distance on Maps rather than committing to an hour wait."
            ),
            "extra": (
                "Bankara’s kakuni is fattier than standard chashu — if you already ate a heavy lunch, stick to the regular size. "
                "Spicy tare can mask the broth; try the standard bowl first if you want to taste the base soup. "
                "Ikebukuro East Exit side is usually the shortest walk from the station — use Maps street view if it is your first time in the area."
            ),
        },
        "ko": {
            "order": "기본 돈코츠·반카라 시그니처 — 매운맛·토핑은 두 번째 방문에",
            "hook": (
                "이케부쿠로 반카라 라멘은 진한 돈코츠·쇼유와 늦은 영업으로 유명합니다. "
                "1998년경 이케부쿠로에서 시작한 ‘묵직한’ 돈코츠 계열로, 세아부라(지방)와 "
                "카쿠니(조림 돼지) 토핑이 브랜드 특징입니다. 주변 가게가 문 닫은 뒤 대안으로 찾는 경우도 많습니다. "
                "‘배부르게 한 그릇’을 원할 때 고르는 손님이 많고, 가벼운 점심보다는 저녁·야식에 가깝습니다."
            ),
            "bowl": (
                "돈코츠에 쇼유 다레가 얹힌 진한 국물, 카쿠니·차슈 토핑이 포인트입니다. "
                "매운 버전·토핑 추가 메뉴가 메뉴판에 자주 있습니다. 도쿄 중심부 기준 ¥1,000~¥1,300 전후. "
                "첫 방문은 시그니처 돈코츠 또는 ‘반카라’ 명칭 그릇으로 시작하는 것이 안전합니다. "
                "카쿠니는 입에서 살살 녹는 편이라, 면과 번갈아 먹으면 느끼함이 덜할 수 있습니다."
            ),
            "visit": (
                "저녁 7~10시·야간에 손님이 몰립니다. 15~25분 대기가 있을 수 있으나 줄은 꾸준히 줄어듭니다. "
                "카운터 위주라 2~3명 이상이면 붙어 앉기 어려울 수 있습니다. "
                "키오스크는 사진·¥ 가격으로 고를 수 있습니다. 라스트 오더는 지도에서 확인하세요. "
                "이케부쿠로는 마지막 열차 전에 손님이 몰리는 경우가 있어, 22시 전후에도 잠깐 줄이 생길 수 있습니다."
            ),
            "area": (
                "이케부쿠로 역은 야마노테선 허브로, 선샤인시티·호텔·야간 편의점과 연결됩니다. "
                "도쿄 서북부 숙소나 이케부쿠로 저녁 일정 뒤 ‘늦은 라멘’ 슬롯에 넣기 좋습니다. "
                "야간 라멘 후에는 역 지하 상가·konbini로 바로 이어지는 동선이 많아, ‘마지막 한 그릇’ 계획에 잘 맞습니다."
            ),
            "extra": (
                "카쿠니는 일반 차슈보다 지방이 많습니다 — 점심을 heavy하게 먹었다면 보통 사이즈를 권합니다. "
                "매운맛은 국물 맛을 가릴 수 있어, 첫 방문은 기본 맛으로 국물 간을 확인하는 편이 좋습니다. "
                "이케부쿠로 동쪽 출구 쪽이 역에서 가깝게 나오는 경우가 많습니다. 처음이면 지도 거리뷰로 입구를 확인하세요. "
                "늦은 시간 방문 시 주변 상점이 닫혀도 반카라만큼은 영업하는 경우가 있어, ‘마지막 한 그릇’ 후보로 메모해 두면 유용합니다. "
                "키오스크에서 사진·¥ 숫자만 보고 고를 수 있지만, ‘카쿠니’가 들어간 메뉴는 토핑이 무거우니 면 사이즈는 보통으로 시작하세요. "
                "2~3명이면 카운터가 분리될 수 있어, 붙어 앉기 어렵다면 순번대로 들어가는 것이 일반적입니다."
            ),
            "extra2": (
                "이케부쿠로는 JR·지하철·西武線 등 노선이 겹쳐, ‘이케부쿠로’만 검색하면 다른 출구로 나올 수 있습니다. "
                "늦은 시간 방문 후에는 역 주변 24시간 konbini·ATM이 있어 현금 보충이 비교적 쉽습니다. "
                "진한 국물 후 속이 더부룩할 수 있으니, 다음 일정은 가벼운 산책이나 카페로 잡는 편이 편합니다. "
                "반카라는 ‘듬뿍 토핑’ 이미지가 강해, 면을 다 못 먹고 남기는 경우도 있습니다 — 보통 사이즈로 시작하세요. "
                "이케부쿠로 동쪽·서쪽 출구 중 어디가 가까운지 지도 리뷰 사진을 한 번 확인하면 헤매는 시간을 줄일 수 있습니다. "
                "카쿠니 토핑은 국물보다 먼저 식을 수 있어, 제공 직후 고기부터 번갈아 먹는 편이 좋습니다. "
                "이케부쿠로 야간 라멘은 ‘마지막 한 그릇’ 후보로 자주 거론됩니다."
            ),
        },
    },
    "menya_musashi_shinjuku": {
        "en": {
            "order": "Black or red W-soup (dual-broth) signature bowl; kaedama if you finish broth with noodles left.",
            "hook": (
                "Menya Musashi Shinjuku is the flagship of a chain founded by a former student of the original Musashi style — "
                "famous for W-soup (dual broth): tonkotsu blended with a second stock for depth without pure white Hakata heaviness. "
                "The Shinjuku location sits in one of Tokyo’s busiest dining zones; lunch and dinner queues are normal, not a sign of trouble."
            ),
            "bowl": (
                "Look for black (garlic-forward) or red (spicy) W-soup bowls on the menu — both use the dual-broth base with different tare. "
                "Noodles are typically firm and straight; toppings include chashu, egg, and nori depending on the set. "
                "Kaedama (extra noodles) is offered at many Musashi shops if you have broth left. Prices around ¥1,000–¥1,400. "
                "This branch is ramen-in-broth style, not tsukemen — do not confuse with other Musashi spin-offs that specialize in dipping noodles."
            ),
            "visit": (
                "Weekday lunch 11:30–13:30 and weekend dinner are busiest. Ticket machine near the entrance — buy before sitting if instructed. "
                "Counter seats fill in waves; solo diners get seated faster than large groups. "
                "English on the machine is limited; follow the top-row photos for ‘recommended’ bowls. No reservations."
            ),
            "area": (
                "Walkable from Shinjuku Station’s east and south exits — easy to combine with Kabukicho, Shinjuku Gyoen, or a transfer-day stop. "
                "If the queue exceeds 30 minutes, consider another Shinjuku tonkotsu shop on the map for the same trip rather than one shop only."
            ),
            "extra": (
                "Black (garlic) and red (spicy) bowls share the same W-soup base — pick one, not both on a first visit. "
                "Kaedama is only worth it if you have broth left; Musashi portions are already filling. "
                "Shinjuku Station has many exits; pin the shop on Maps before you leave the ticket gates to avoid a long walk."
            ),
        },
        "ko": {
            "order": "블랙·레드 W스프(쌍육수) 시그니처 — 국물 남으면 가에다마(면 추가) 확인",
            "hook": (
                "멘야 무사시 신주쿠는 쌍육수(W스프) 돈코츠로 유명한 체인의 대표 지점입니다. "
                "돈코츠에 다른 육수를 섞어 깊이를 내는 방식으로, 순백색 하카타 돈코츠만큼 무겁지 않게 느껴지는 경우가 많습니다. "
                "신주쿠라 점심·저녁 웨이팅은 흔합니다. "
                "1960년대부터 이어진 ‘무사시’ 계열 중 신주쿠 지점은 관광객·출장객 모두에게 이름이 많이 알려져 있습니다."
            ),
            "bowl": (
                "메뉴판에서 블랙(마늘)·레드(매운맛) W스프를 찾으면 됩니다. "
                "면은 탄력 있는 직면, 차슈·味玉·김 토핑 세트가 일반적입니다. "
                "국물이 남으면 가에다마(면 추가)를 요청할 수 있는 매장이 많습니다. ¥1,000~¥1,400 전후. "
                "이 지점은 국물 라멘이며, 츠케멘 전문 다른 ‘무사시’ 계열과 혼동하지 마세요. "
                "W스프는 첫 모금에서 ‘고소한 육수+돈코츠’가 함께 느껴지는 경우가 많습니다."
            ),
            "visit": (
                "평일 점심 11:30~13:30, 주말 저녁이 가장 붐빕니다. "
                "입구 식권기에서 먼저 구매하는 경우가 많습니다. "
                "1인석 회전이 빨라 혼자보다 3인 이상은 대기가 길어질 수 있습니다. 예약 없음. "
                "신주쿠 역에서 5~10분 걸릴 수 있으니, 지도 핀을 미리 저장해 두면 좋습니다."
            ),
            "area": (
                "신주쿠역 동·남쪽 출구에서 도보권입니다. "
                "가부키초·신주쿠御苑 당일 일정 중 한 끼로 넣기 좋습니다. "
                "신주쿠 환승일에 ‘한 그릇만’ 넣기 좋은 위치라, 도쿄 여행 초반·중반 모두 후보로 두기 쉽습니다."
            ),
            "extra": (
                "블랙(마늘)·레드(매운맛)는 같은 W스프 베이스입니다 — 첫 방문에 두 그릇을 비교하려면 친구와 나눠 주문하는 편이 낫습니다. "
                "가에다마는 국물이 남았을 때만 의미 있습니다. 기본 그릇도 든든한 편입니다. "
                "신주쿠역 출구가 많으니, 개찰구 나가기 전 지도에 가게를 고정해 두면 헤매는 시간을 줄일 수 있습니다. "
                "무사시는 ‘면이 탄력 있다’는 평이 많아, 제공 후 5분 이상 두면 맛이 떨어질 수 있습니다 — 사진은 짧게. "
                "신주쿠는 관광·출장객이 섞여 있어 혼잡하지만, 1인석 위주라 혼자 방문해도 부담이 적습니다. "
                "W스프는 돈코츠만큼 느끼하지 않다고 느끼는 분도 있지만, 마늘 블랙은 향이 강하니 마늘을 싫어하면 레드·기본 계열을 고르세요."
            ),
            "extra2": (
                "신주쿠는 바쁜 역이라 GPS가 튀는 경우가 있습니다 — 가게 앞까지 ‘도보’ 내비를 켠 뒤 마지막 100m는 간판으로 확인하세요. "
                "점심 시간대에는 주변 오피스 직장인 비중이 높아, 주말 관광객과 패턴이 다릅니다. "
                "면이 먼저 나오면 국물보다 빨리 식을 수 있으니, 제공 직후 바로 시작하는 것이 좋습니다. "
                "무사시는 신주쿠 ‘대표’ 라멘 중 하나라 검색 결과가 많습니다 — 주소·간판 사진이 이 지점과 맞는지 꼭 확인하세요. "
                "블랙·레드 선택이 고민되면, 마늘·매운맛 모두 괜찮다면 블랙이 더 ‘무사시’스러운 경우가 많습니다. "
                "점심 대기가 길면, 신주쿠 역 주변 다른 돈코츠를 지도에서 비교해 보는 것도 방법입니다. "
                "무사시는 신주쿠에서 ‘첫 돈코츠’로 많이 선택되지만, W스프가 낯설다면 기본·레드부터 시도해 보세요. "
                "식권기에서 고민될 때는 사진이 큰 버튼·첫 줄 메뉴를 고르면 실패 확률이 낮습니다. "
                "신주쿠 동쪽·남쪽 출구 중 어디로 나올지 미리 정해 두면 도착 후 헤매는 시간을 줄일 수 있습니다."
            ),
        },
    },
    "ramen_shingen": {
        "en": {
            "order": "House miso ramen; butter-corn or spicy miso if you want classic Sapporo toppings.",
            "hook": (
                "Ramen Shingen has operated in Susukino, Sapporo since 1988 — a long-running miso specialist in Hokkaido’s main nightlife district. "
                "Unlike the multi-stall Ganso Ramen Yokocho alley nearby, this is a single-brand shop with one house style. "
                "Winter evenings and post-ski season bring long queues; summer is slightly calmer but dinner still busy."
            ),
            "bowl": (
                "Sapporo miso: miso tare is often stir-fried before meeting pork-chicken broth, with thick curly noodles. "
                "Butter, sweet corn, and spicy miso (karami-miso) variants appear on the menu — classic Hokkaido comfort toppings. "
                "One regular bowl is filling; ¥900–¥1,200 is typical. Start with standard miso before ordering the largest size."
            ),
            "visit": (
                "Expect 20–40 minute waits at peak dinner in winter. Ticket machine or counter order — confirm cash/card at the door. "
                "Counter-only seating means you may share elbow space with neighbors. Eat hot — noodles soften if you wait. "
                "No English menu guaranteed; photos and ‘miso’ kanji (味噌) identify the main line."
            ),
            "area": (
                "Susukino is Sapporo’s bar and restaurant core, walkable from Susukino or Nakajima-Koen Station. "
                "Pair with Ganso Ramen Yokocho on a different night to compare alley vs single-shop miso. "
                "After skiing at Niseko or Teine, many travelers stop here before hotels — plan a buffer for the queue."
            ),
            "extra": (
                "Sapporo miso is heavier than Tokyo shoyu — one bowl plus a side is rarely needed. "
                "Butter and corn add sweetness; skip them if you want a cleaner miso taste. "
                "Susukino addresses can look similar at night — confirm the shop name in kanji (信玄) on the sign before you join the wrong queue."
            ),
        },
        "ko": {
            "order": "기본 미소 라멘 — 버터·옥수수·매운 미소는 삿포로식 토핑",
            "hook": (
                "라멘 신겐은 1988년부터 스스키노에서 운영하는 삿포로 미소 전문점입니다. "
                "원조 라멘 요코초 골목과 달리 단일 브랜드 매장입니다. "
                "겨울 저녁·스키 시즌에 줄이 길어지며, 여름은 상대적으로 한산하지만 저녁은 여전히 붐빕니다. "
                "홋카이도 여행에서 ‘미소 한 그릇’을 제대로 맛보려는 분들이 줄을 서는 편입니다."
            ),
            "bowl": (
                "볶은 미소 다레와 돼지·닭 육수, 곱은 면이 전형적입니다. "
                "버터·옥수수·가라미미소(매운 미소) 옵션이 흔합니다. ¥900~¥1,200 전후. "
                "첫 방문은 기본 미소·보통 사이즈로 충분한 경우가 많습니다. "
                "삿포로 미소는 ‘고소한 누룽지·된장’ 향이 특징인 편이라, 도쿄 미소와 비교해 보면 차이가 큽니다."
            ),
            "visit": (
                "겨울 저녁 20~40분 대기가 있을 수 있습니다. 식권기·현금 여부는 입구 확인. "
                "카운터만 있어 이웃과 가까이 앉을 수 있습니다. "
                "미소는 식기 전에 먹는 편이 좋습니다. ‘味噌’ 한자로 메인 메뉴를 찾을 수 있습니다. "
                "스스키노는 금·토요일 밤에 특히 붐비므로, 평일 저녁이 상대적으로 수월할 수 있습니다."
            ),
            "area": (
                "스스키노·中島公園 역에서 도보권입니다. "
                "요코초 골목과는 다른 날 비교 방문하면 삿포로 미소 차이를 느끼기 쉽습니다. "
                "삿포로 숙소가 스스키노·すすきの 근처라면, 저녁 한 끼·야식 슬롯으로 넣기 좋습니다."
            ),
            "extra": (
                "삿포로 미소는 도쿄 쇼유보다 무겁습니다 — 기본 그릇 하나면 충분한 경우가 많습니다. "
                "버터·옥수수는 단맛이 강해, 맑은 미소 맛을 원하면 빼고 주문할 수 있는지 메뉴판을 확인하세요. "
                "스스키노는 밤에 비슷한 간판이 많습니다 — ‘信玄’ 한자 간판을 확인하고 줄을 서세요. "
                "겨울철 실내 난방+뜨거운 국물로 땀이 날 수 있어, 코트는 의자 등받이에 걸 수 있는지 확인하세요. "
                "스키·겨울 여행 중이라면 신겐 한 그릇 후 디저트까지 계획하기엔 배가 찰 수 있습니다 — 저녁 메인으로만 잡는 편이 낫습니다. "
                "미소 라멘은 국물이 진해 면이 빨리 눅눅해질 수 있으니, 대화보다 식사에 집중하면 만족도가 높습니다."
            ),
            "extra2": (
                "삿포로는 겨울에 실내·실외 온도차가 커서, 코트·장갑을 의자에 걸 수 있는지 먼저 확인하세요. "
                "스스키노는 술집·라멘·곱창 골목이 섞여 있어, 밤 10시 이후에도 주변은 활기 있지만 가게별 라스트 오더는 다릅니다. "
                "홋카이도 여행 마지막 날 ‘미소 한 그릇’으로 마무리하려면, 짐을 호텔에 두고 가볍게 방문하는 동선이 좋습니다. "
                "신겐은 요코초 ‘여러 가게 비교’와 달리 한 메뉴에 집중한 곳이라, 줄이 길어도 ‘이 집만’ 맛보고 싶을 때 선택합니다. "
                "겨울철 실내가 더울 수 있어, 두꺼운 외투는 의자에 걸어두고 먹는 편이 편합니다. "
                "줄이 길 때는 지도 리뷰의 ‘최근’ 사진으로 메뉴판 변경 여부를 확인하면 주문 실수를 줄일 수 있습니다. "
                "신겐은 스스키노 ‘미소’ 대표 후보 중 하나라, 겨울 여행 일정표에 ‘저녁 미소’ 슬롯으로 미리 넣어 두면 좋습니다. "
                "버터·옥수수 토핑은 따뜻한 날에도 인기가 많아, ‘무겁다’고 느끼면 빼고 주문할 수 있는지 메뉴판을 확인하세요. "
                "스스키노는 밤늦게도 활기 있지만 가게별 라스트 오더가 다르므로, 방문 전 지도 영업시간을 꼭 확인하세요."
            ),
        },
    },
    "muteppou_kyoto": {
        "en": {
            "order": "Signature kotteri tonkotsu; kaedama only if you finish noodles — the broth is very rich.",
            "hook": (
                "Muteppou Kyoto (in Kizugawa, south of central Kyoto) is known for kotteri — extremely thick, dark pork-bone broth. "
                "This is the opposite of light Kyoto shoyu: one bowl is heavy, and many diners treat it as a dedicated dinner, not a quick snack. "
                "The shop draws tonkotsu fans from Kyoto city; check Maps for the exact address — it is not in the temple district."
            ),
            "bowl": (
                "Broth is reduced until opaque and collagen-rich — darker than typical Hakata white tonkotsu. "
                "Thin noodles are common to balance the soup weight. Kaedama culture exists but the broth alone is filling. "
                "Start with the signature tonkotsu; avoid ordering large size on an empty stomach if you plan more food later. Roughly ¥900–¥1,200."
            ),
            "visit": (
                "Queues at lunch and dinner; counter-focused layout. Access is easier by train or car than walking from Gion — verify route on Maps. "
                "Irregular closing days are common for suburban Kyoto shops — check Monday/holiday rules before you travel. "
                "Cash and ticket machines are typical; eat promptly while the fat emulsion is hot."
            ),
            "area": (
                "Kizugawa area suits travelers with a car or those combining southern Kyoto with Nara day trips. "
                "After temple-heavy days in Higashiyama, this is a ‘heavy reward bowl’ — not for the same day as a light kaiseki dinner. "
                "Compare with Honke Daiichi Asahi shoyu on another day to see Kyoto’s two ramen extremes."
            ),
            "extra": (
                "Kotteri broth coats the lips — bring a small towel if you care about that after eating. "
                "Kaedama is optional; many first-timers cannot finish the soup alone. "
                "If you are staying in central Kyoto without a car, compare travel time on Maps — a 40-minute round trip for one bowl may not fit a tight temple day."
            ),
        },
        "ko": {
            "order": "시그니처 코테리 돈코츠 — 국물이 매우 진해 가에다마는 배 고려 후",
            "hook": (
                "무테포 교토(기즈가와·교토 남부)는 코테리(극진) 돈코츠로 유명합니다. "
                "맑은 교토 쇼유와 반대로, 한 그릇이 무겁고 저녁 한 끼로 계획하는 손님이 많습니다. "
                "교토 시내 사찰 동선과는 거리가 있으니 지도에서 접근 경로를 먼저 확인하세요. "
                "‘국물이 진짜 진하다’는 평이 많아, 돈코츠 매니아·진한 맛 선호자에게 맞는 편입니다."
            ),
            "bowl": (
                "국물은 흰 백탕보다 진하고 어두운 돼지뼈 농축 타입입니다. "
                "진한 국물에 맞춰 가는 면이 흔합니다. 가에다마가 있어도 국물만으로 배가 차는 경우가 많습니다. "
                "시그니처 돈코츠·보통 사이즈로 시작하세요. ¥900~¥1,200 전후. "
                "국물 표면의 기름층이 두껍게 느껴질 수 있으니, 첫 몇 숟가락으로 간·진하기를 확인하세요."
            ),
            "visit": (
                "점심·저녁 웨이팅, 카운터 중심 좌석. 기즈가와는 도보 관광지와 떨어져 있어 교통 계획이 필요합니다. "
                "월요일·연휴 휴무가 잦을 수 있으니 지도 휴무일 확인. "
                "식권기·현금 규칙은 입구 안내를 따르세요. "
                "주차장이 있는 경우도 있으니, 렌터카 이용 시 지도 ‘주차’ 정보를 함께 확인하세요."
            ),
            "area": (
                "남부 교토·奈良 당일치기와 묶을 수 있습니다. "
                "혼케 다이이치 아사히 쇼유와 다른 날 비교하면 교토 라멘의 양극단을 경험할 수 있습니다. "
                "교토 시내 숙소만 있다면, ‘무거운 돈코츠 하루’를 따로 잡는 일정표가 편합니다."
            ),
            "extra": (
                "코테리 국물은 입술에 기름막이 남을 수 있습니다 — 신경 쓰이면 작은 손수건을 챙기세요. "
                "가에다마 없이도 배가 차는 손님이 많습니다. "
                "교토 시내 숙소만 있다면 지도로 이동 시간을 먼저 보세요 — 당일 사찰 일정이 빡빡하면 왕복 40분이 부담일 수 있습니다. "
                "기즈가와·교토 남부는 ‘관광지 한복판’이 아니라, 현지인·돈코츠 마니아 비중이 높은 편입니다. "
                "국물이 매우 진해 소금기가 강하게 느껴질 수 있으니, 첫 몇 숟가락으로 간을 확인한 뒤 식초·고추를 넣으세요. "
                "혼케 다이이치 아사히(맑은 쇼유)와 같은 여행에서 둘 다 가려면, 하루는 가벼운 점심·하루는 저녁 든든히 나누는 일정이 좋습니다."
            ),
            "extra2": (
                "기즈가와·교토 남부는 버스·택시·렌터카 접근이 흔합니다 — ‘교토역에서 20분’ 같은 표현은 교통수단에 따라 크게 달라집니다. "
                "코테리 국물은 속이 더부룩할 수 있어, 다음 날 아침 가벼운 일정을 두는 편이 좋습니다. "
                "돈코츠를 처음 접한다면, 무테포보다 먼저 가벼운 쇼유를 먹고 오는 것도 소화·비교에 도움이 됩니다. "
                "무테포는 ‘교토=맑은 라멘’ 이미지와 달리, 돈코츠 매니아용으로 기대치를 맞추는 것이 중요합니다. "
                "차로 간다면 주차·마감 시간을 지도에서 미리 확인하세요. "
                "코테리는 ‘국물까지 다 마신다’는 부담보다, 면과 토핑 위주로 즐겨도 충분한 경우가 많습니다. "
                "교토 여행에서 ‘무거운 돈코츠 하루’를 따로 잡는다면, 무테포는 저녁·점심 중 한 끼로 집중하는 편이 좋습니다. "
                "기즈가와는 ‘교토=맑은 라멘’ 이미지와 거리가 있으니, 방문 전 기대치를 ‘진한 돈코츠’로 맞추는 것이 중요합니다. "
                "교토역·기즈가와역 등 접근 경로가 여러 가지라, 숙소 위치에 맞는 노선을 지도에서 비교해 보세요. "
                "코테리 국물은 한 그릇으로도 포만감이 크니, 같은 날 가벼운 카페·디저트 일정과 겹치지 않게 잡는 편이 좋습니다."
            ),
        },
    },
    "fuunji_shinjuku": {
        "en": {
            "order": "Standard tsukemen set; ask for soup-wari (broth dilution) after noodles if offered.",
            "hook": (
                "Fuunji Shinjuku (風雲児) is a tsukemen specialist near Yoyogi — noodles and concentrated dipping broth served separately, not a soup bowl. "
                "The dip blends chicken and seafood stock for a thick, umami-heavy tsuke soup. "
                "Lunch queues of 30–60 minutes are common on weekdays; the shop has Bib Gourmand recognition, which adds tourist traffic."
            ),
            "bowl": (
                "Order tsukemen (つけ麺). Cold or room-temp noodles go into a separate bowl; dip each bite into the hot concentrated broth. "
                "Noodle firmness is the focus — eat within 10 minutes of serving. "
                "When finished, staff may offer soup-wari: hot water or light broth added to the remaining dip so you can drink it. "
                "Sizes and spice levels vary; start regular unless you are very hungry. About ¥900–¥1,200."
            ),
            "visit": (
                "Arrive before 11:30 a.m. for shorter lines, or accept a long lunch wait. Ticket machine at entrance — buy before queueing if signs say so. "
                "No lingering after finishing; turnover matters. Solo diners seated faster. "
                "Closed some Mondays — verify on Maps. Not ideal for large luggage at crowded counter."
            ),
            "area": (
                "Yoyogi / west Shinjuku — combine with Meiji Shrine morning walk and lunch here, or office-district weekday trip. "
                "Tsukemen fills you quickly; plan a light dinner. Other Shinjuku tsukemen shops are different styles — compare on separate days."
            ),
            "extra": (
                "Do not pour the dip into the noodle bowl — dip each bite. "
                "If soup-wari is offered, say yes before you stand up; staff may not repeat the offer. "
                "Phone photos in tight counter rows can annoy neighbors — one quick shot is enough."
            ),
        },
        "ko": {
            "order": "기본 츠케멘 — 면 다 먹은 뒤 스프 와리(육수 희석) 가능하면 요청",
            "hook": (
                "후운지 신주쿠(風雲児)는 요요기 인근 츠케멘 전문점으로, 국물 라멘이 아닌 ‘찍어먹는 면’ 스타일입니다. "
                "닭·생선 육수를 농축한 찍어먹기 국물이 특징이며, 평일 점심 30~60분 대기가 흔합니다. "
                "빕 구르망 선정으로 관광객 비중도 높습니다. "
                "면 식감·진한 육수를 우선할 때 신주쿠에서 가장 먼저 거론되는 츠케멘 중 하나입니다."
            ),
            "bowl": (
                "츠케멘(つけ麺)을 주문합니다. 면과 뜨거운 농축 육수가 분리 제공됩니다. "
                "면 식감이 핵심이라 제공 후 10분 안에 먹는 편이 좋습니다. "
                "다 먹으면 스프 와리로 남은 육수를 희석해 마실 수 있는 경우가 있습니다. ¥900~¥1,200 전후. "
                "찍어먹기 육수는 라멘 국물보다 훨씬 진하므로, 면을 충분히 적셔 한 입씩 드세요."
            ),
            "visit": (
                "11:30 이전 도착이 줄이 짧습니다. 입구 식권기 — 안내에 따라 줄 서기 전 구매. "
                "식사 후 자리 오래 잡지 않는 것이 매너입니다. 1인석 회전이 빠릅니다. "
                "월요일 휴무인 경우가 있어 지도 확인. 큰 캐리어는 혼잡한 카운터에서 불편할 수 있습니다. "
                "점심 피크에는 서서 기다리는 동안 메뉴를 미리 정해 두면 주문이 빨라집니다."
            ),
            "area": (
                "요요기·신주쿠 서쪽 — 메이지 신궁 아침 산책 후 점심으로 묶기 좋습니다. "
                "츠케멘은 배가 빨리 차므로 저녁은 가볍게 계획하세요. "
                "오므라이스·카페가 많은 요요기 일대와 달리, 후운지는 ‘한 가지에 집중’하는 점심 코스입니다."
            ),
            "extra": (
                "육수를 면 그릇에 붓지 마세요 — 한 입씩 찍어 먹는 스타일입니다. "
                "스프 와리를 제공하면 일어나기 전에 요청하세요 — 나중에 다시 물어보지 않을 수 있습니다. "
                "카운터가 좁을 때 사진 촬영은 짧게 — 이웃 손님 방해가 될 수 있습니다. "
                "점심 피크(12~13시)에는 30~60분 대기가 흔합니다 — 메이지 신궁 아침 일정과 묶을 때는 버퍼 1시간을 두세요. "
                "면은 제공 직후가 가장 탄력 있습니다 — 사진·SNS보다 먼저 한 젓가락 드세요. "
                "츠케멘은 국물 라면보다 배가 빨리 차므로, 오후에 가벼운 카페·디저트 일정과 겹치지 않게 계획하면 좋습니다."
            ),
            "extra2": (
                "요요기·신주쿠 서쪽은 점심에 오피스·관광객이 섞입니다 — 비 오는 날에도 실내 대기 줄이 길어질 수 있습니다. "
                "츠케멘은 국물을 거의 다 마시면 짠맛이 강해질 수 있어, 스프 와리를 권하는 이유입니다. "
                "메이지 신궁과 같은 반나절 동선으로 묶을 때, 신궁→후운지 순이 지리적으로 자연스러운 경우가 많습니다. "
                "후운지는 ‘츠케멘 입문’으로도 많이 찾지만, 점심 대기가 길어 ‘입문’ 전에 시간 여유를 확보하는 편이 좋습니다. "
                "육수 그릇은 뜨거우니, 면을 옮길 때 손·소매에 튀지 않게 조심하세요. "
                "대기 줄이 실내가 아닌 경우도 있으니, 여름·겨울 외투를 미리 정리해 두면 편합니다. "
                "후운지는 츠케멘 ‘입문+만족’을 동시에 노리는 손님이 많아, 점심 시간대만큼은 일정을 비워 두는 편이 낫습니다. "
                "신주쿠·하라주쿠 쇼핑과 같은 날이라면, 쇼핑 전·후 중 ‘배가 고픈은 시간’에 맞춰 줄 서는 전략이 효율적입니다. "
                "츠케멘은 면과 육수가 분리되어 나와, 제공 직후 10분 안에 먹는 것이 식감·온도 모두 가장 좋습니다. "
                "요요기 일대는 점심·저녁 모두 사람이 많으니, 후운지 방문일에는 주변 식당 예약·대기 시간을 함께 고려하세요. "
                "월요일 휴무 여부는 지도에서 최신 정보를 확인하세요."
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


FEATURED_SHOP_SLUGS = frozenset(
    {
        "honke_daiichi-asahi",
        "menya_musashi_shinjuku",
        "ramen_shingen",
        "bankara_ramen",
        "muteppou_kyoto",
        "fuunji_shinjuku",
    }
)


SEO_OVERRIDES: dict[str, dict[str, dict[str, str]]] = {
    "menya_musashi_shinjuku": {
        "en": {
            "seo_title": "Menya Musashi Shinjuku: W-soup tonkotsu guide | OKRamen",
            "seo_description": (
                "Practical guide to Menya Musashi Shinjuku in Tokyo: W-soup (dual-broth) tonkotsu, "
                "black and red bowls, ticket machine tips, and typical queue times. "
                "This branch serves ramen in broth, not tsukemen — confirm hours on Google Maps."
            ),
            "description": (
                "Visitor guide to Menya Musashi Shinjuku: W-soup tonkotsu ramen, what to order, "
                "queue tips, and ticket machine notes for the Shinjuku flagship."
            ),
        },
    },
    "fuunji_shinjuku": {
        "en": {
            "seo_title": "Fuunji Shinjuku: tsukemen queue and ordering guide | OKRamen",
            "seo_description": (
                "How to visit Fuunji near Yoyogi: lunch wait times, tsukemen ordering, "
                "soup-wari after noodles, and local tips. Verify hours and Monday closures on Google Maps."
            ),
            "description": (
                "Practical guide to Fuunji in Shinjuku — chicken-seafood tsukemen, typical lunch queues, "
                "ticket machine, and how to finish with soup-wari."
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
        p_extra = override.get("extra", "")
        p6 = local_tip(lang, base, late)
        p7 = maps_footer(lang, shop_name)
        extra_label = "주문·매너" if lang == "ko" else "Ordering notes"
        parts = [
            paragraph(l1, p1),
            paragraph(l2, p2),
            paragraph(l3, p3),
            paragraph(l4, p4),
        ]
        if p_extra.strip():
            parts.append(paragraph(extra_label, p_extra))
        p_extra2 = override.get("extra2", "")
        if p_extra2.strip():
            parts.append(paragraph("현지 팁" if lang == "ko" else "Local tip", p_extra2))
        parts.extend(
            [
                paragraph(l5, p5),
                paragraph("", p6),
                paragraph("", p7),
            ]
        )
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

    seo_pack = SEO_OVERRIDES.get(base, {}).get(lang)
    if seo_pack:
        meta.update(seo_pack)

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
    featured_only = "--featured" in sys.argv
    region_index = build_region_index()
    ok = 0
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if featured_only and base_slug(path.stem) not in FEATURED_SHOP_SLUGS:
            continue
        if template_only and not needs_practical_rewrite(path):
            continue
        rewrite_file(path, region_index, dry_run=dry)
        ok += 1
    label = "featured " if featured_only else ("template " if template_only else "")
    print(f"Rewrote {ok} {label}ramen files{' (dry-run)' if dry else ''}")


if __name__ == "__main__":
    main()
