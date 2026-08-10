"""Legacy URL redirects for GSC 404 / soft page cleanup."""

from __future__ import annotations

import os
import re

# Exact path -> destination (301). Paths without query string.
RAMEN_REDIRECTS: dict[str, str] = {
    # Slug typo
    "nagahama_no_1_en": "/ramen/nagahama_no.1_en",
    "nagahama_no_1_ko": "/ramen/nagahama_no.1_ko",
    # Related surviving shops
    "ichiran_fukuoka_main_en": "/ramen/ichiran_shinjuku_en",
    "ichiran_fukuoka_main_ko": "/ramen/ichiran_shinjuku_ko",
    "mennoya_kyoto_en": "/ramen/mennoya_en",
    "mennoya_kyoto_ko": "/ramen/mennoya_ko",
    # Deleted shops -> topical hubs
    "aji_no_kura_en": "/guide/regional_ramen_en",
    "aji_no_kura_ko": "/guide/regional_ramen_ko",
    "menya_masamoto_en": "/guide/regional_ramen_en",
    "menya_masamoto_ko": "/guide/regional_ramen_ko",
    "menya_saita_en": "/guide/regional_ramen_en",
    "menya_saita_ko": "/guide/regional_ramen_ko",
    "ramen_ore-no-sora_en": "/guide/regional_ramen_en",
    "ramen_ore-no-sora_ko": "/guide/regional_ramen_ko",
    "yatai_ramen_mamigichan_en": "/guide/regional_ramen_en",
    "yatai_ramen_mamigichan_ko": "/guide/regional_ramen_ko",
    "ramen_shirakaba_sansou_en": "/guide/regional_ramen_en",
    "ramen_shirakaba_sansou_ko": "/guide/regional_ramen_ko",
    "ramen_kairyu_en": "/guide/regional_ramen_en",
    "ramen_kairyu_ko": "/guide/regional_ramen_ko",
    "yamei_ramen_en": "/guide/regional_ramen_en",
    "yamei_ramen_ko": "/guide/regional_ramen_ko",
    "tairyo_ramen_en": "/guide/regional_ramen_en",
    "tairyo_ramen_ko": "/guide/regional_ramen_ko",
    "tantanmen_sandaime_en": "/guide/regional_ramen_en",
    "tantanmen_sandaime_ko": "/guide/regional_ramen_ko",
    "ramen_nagi_shinjuku_en": "/guide/tokyo_ramen_street_en",
    "ramen_nagi_shinjuku_ko": "/guide/tokyo_ramen_street_ko",
    "ramen_sapporo_akaboshi_en": "/guide/sapporo_miso_legend_en",
    "ramen_sapporo_akaboshi_ko": "/guide/sapporo_miso_legend_ko",
}

# Deleted / consolidated guides -> best remaining URL
GUIDE_REDIRECTS: dict[str, str] = {
    "LINK_TO_MAP": "/",
    "instant_ramen_hacks_en": "/guide/instant_vs_shop_en",
    "instant_ramen_hacks_ko": "/guide/instant_vs_shop_ko",
    "ramen_ordering_hacks_en": "/guide/how_to_order_en",
    "ramen_ordering_hacks_ko": "/guide/how_to_order_ko",
    "ramen_inflation_prices_en": "/guide/ramen_prices_en",
    "ramen_inflation_prices_ko": "/guide/ramen_prices_ko",
    "female_solo_ramen_en": "/guide/solo_traveler_ramen_en",
    "female_solo_ramen_ko": "/guide/solo_traveler_ramen_ko",
    "family_friendly_ramen_en": "/guide",
    "family_friendly_ramen_ko": "/guide?lang=ko",
    "ramen_for_celebrations_en": "/guide",
    "ramen_for_celebrations_ko": "/guide?lang=ko",
    "ramen_for_tourists_tips_en": "/guide/how_to_order_en",
    "ramen_for_tourists_tips_ko": "/guide/how_to_order_ko",
    "ramen_for_cold_weather_en": "/guide/seasonal_ramen_en",
    "ramen_for_cold_weather_ko": "/guide/seasonal_ramen_ko",
    "ramen_making_workshop_en": "/guide",
    "ramen_making_workshop_ko": "/guide?lang=ko",
    "ramen_museum_guide_en": "/guide",
    "ramen_museum_guide_ko": "/guide?lang=ko",
    "kitakata_wide_noodles_en": "/guide/regional_ramen_en",
    "kitakata_wide_noodles_ko": "/guide/regional_ramen_ko",
    "wakayama_ramen_style_en": "/guide/regional_ramen_en",
    "wakayama_ramen_style_ko": "/guide/regional_ramen_ko",
    "onimichi_fish_broth_en": "/guide/regional_ramen_en",
    "onimichi_fish_broth_ko": "/guide/regional_ramen_ko",
    "ajitama_secrets_en": "/guide/essential_toppings_en",
    "ajitama_secrets_ko": "/guide/essential_toppings_ko",
    "ramen_bowl_design_en": "/guide",
    "ramen_bowl_design_ko": "/guide?lang=ko",
    "ramen_business_success_en": "/guide",
    "ramen_business_success_ko": "/guide?lang=ko",
    "ramen_and_coffee_pairing_en": "/guide/ramen_and_drink_en",
    "ramen_and_coffee_pairing_ko": "/guide/ramen_and_drink_ko",
    "ramen_and_seafood_toppings_en": "/guide/essential_toppings_en",
    "ramen_and_seafood_toppings_ko": "/guide/essential_toppings_ko",
    "ramen_and_social_media_en": "/guide",
    "ramen_and_social_media_ko": "/guide?lang=ko",
    "ramen_delivery_apps_en": "/guide",
    "ramen_delivery_apps_ko": "/guide?lang=ko",
    "ramen_diet_options_en": "/guide/healthy_ramen_tips_en",
    "ramen_diet_options_ko": "/guide/healthy_ramen_tips_ko",
    "ramen_packaging_design_en": "/guide",
    "ramen_packaging_design_ko": "/guide?lang=ko",
    "ramen_seasonal_limited_en": "/guide/seasonal_ramen_en",
    "ramen_seasonal_limited_ko": "/guide/seasonal_ramen_ko",
    "ramen_shop_queuing_apps_en": "/guide/ramen-queue-waiting-systems_en",
    "ramen_shop_queuing_apps_ko": "/guide/ramen-queue-waiting-systems_ko",
    "ramen_queue_etiquette_en": "/guide/ramen-queue-waiting-systems_en",
    "ramen_queue_etiquette_ko": "/guide/ramen-queue-waiting-systems_ko",
    "ramen_spiciness_levels_en": "/guide",
    "ramen_spiciness_levels_ko": "/guide?lang=ko",
    "hidden_gems_tips_en": "/guide/regional_ramen_en",
    "hidden_gems_tips_ko": "/guide/regional_ramen_ko",
    "guide_expand_002_en": "/guide",
    "guide_expand_002_ko": "/guide?lang=ko",
    "guide_seed_002_en": "/guide",
    "guide_seed_002_ko": "/guide?lang=ko",
}

_CAFE_RE = re.compile(
    r"(cafe|coffee|latte|espresso|drip|roast|kissaten|brew|patisserie|"
    r"morning_club|workbench|blend|phoenix)",
    re.I,
)


def _lang_suffix(item_id: str) -> str:
    return "ko" if item_id.endswith("_ko") else "en"


def _guide_home(lang: str) -> str:
    return "/guide?lang=ko" if lang == "ko" else "/guide"


def resolve_ramen_redirect(ramen_id: str) -> str | None:
    if ramen_id in RAMEN_REDIRECTS:
        return RAMEN_REDIRECTS[ramen_id]
    lang = _lang_suffix(ramen_id)
    if _CAFE_RE.search(ramen_id):
        return _guide_home(lang)
    return _guide_home(lang)


def resolve_guide_redirect(guide_id: str) -> str:
    if guide_id in GUIDE_REDIRECTS:
        return GUIDE_REDIRECTS[guide_id]
    return _guide_home(_lang_suffix(guide_id))


def resolve_card_redirect(card_id: str, content_dir: str, guide_dir: str) -> str:
    """Map broken /card/* URLs to the canonical content page or hub."""
    lang = _lang_suffix(card_id)
    ramen_path = os.path.join(content_dir, f"{card_id}.md")
    if os.path.isfile(ramen_path):
        return f"/ramen/{card_id}"
    guide_path = os.path.join(guide_dir, f"{card_id}.md")
    if os.path.isfile(guide_path):
        return f"/guide/{card_id}"

    if card_id in RAMEN_REDIRECTS:
        return RAMEN_REDIRECTS[card_id]
    if card_id in GUIDE_REDIRECTS:
        return GUIDE_REDIRECTS[card_id]
    if _CAFE_RE.search(card_id):
        return _guide_home(lang)

    # Prefer topical hub over bare home when sibling lang exists
    base = card_id.rsplit("_", 1)[0] if card_id.endswith(("_en", "_ko")) else card_id
    other = "en" if lang == "ko" else "ko"
    if os.path.isfile(os.path.join(content_dir, f"{base}_{other}.md")):
        return f"/ramen/{base}_{other}"
    if os.path.isfile(os.path.join(guide_dir, f"{base}_{other}.md")):
        return f"/guide/{base}_{other}"

    return _guide_home(lang)
