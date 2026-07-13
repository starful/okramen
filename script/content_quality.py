"""Quality gates for okramen generation (guides + shop pages).

Prevents repeating the thin-template pattern:
- cafe / seed / expand topics
- shops without real map coordinates + address
- short or fluff bodies
"""

from __future__ import annotations

import re

# Topic IDs that must never be generated again (off-brand / mass-seed).
BLOCKED_GUIDE_IDS = frozenset(
    {
        "guide_seed_001",
        "guide_seed_002",
        "guide_seed_003",
        "guide_expand_001",
        "guide_expand_002",
        "guide_expand_003",
        "guide_expand_004",
        "guide_expand_005",
        "guide_expand_006",
        "guide_expand_007",
        "guide_expand_008",
        "guide_expand_009",
    }
)

BLOCKED_GUIDE_ID_PREFIXES = ("guide_seed_", "guide_expand_")

# Slug / name markers for non-ramen cafe filler.
NON_RAMEN_SLUG_MARKERS = (
    "cafe",
    "latte",
    "roast",
    "espresso",
    "kissaten",
    "dessert",
    "bakery",
    "coffee",
    "brew",
)

BANNED_PHRASES = (
    "soul of the shop",
    "broth analysis",
    "noodle & topping",
    "best ramen in",
    "michelin-standard",
    "미슐랭 스타",
    "definitive guide",
    "ultimate pilgrimage",
    "world-class bowl",
    "as a ramen expert",
)

FORBIDDEN_HEADINGS = frozenset(
    {
        "who this guide is for",
        "how to compare your options",
        "recommended decision process",
        "common mistakes to avoid",
        "final checklist",
        "what changes",
        "when this tends to work",
        "when to be careful",
        "practical takeaway",
    }
)

GUIDE_MIN_CHARS = 4000
RAMEN_MIN_CHARS = 3500
SIBLING_FILL_MIN_CHARS = 5000
MIN_H2 = 3

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
FM_SPLIT = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)

QUALITY_PROMPT_RULES = """
Quality rules (mandatory):
- Write specifically about THIS topic/shop. No interchangeable filler.
- Do NOT use template section titles like "Who This Guide Is For",
  "How to Compare Your Options", "Final Checklist", "What Changes",
  "When This Tends To Work", "Practical Takeaway".
- Use unique ## headings tailored to the topic (at least 3).
- Prefer concrete tips (hours patterns, queue reality, what to order, nearest station).
- Do NOT invent exact yen prices, phone numbers, or Michelin claims.
- Raw Markdown only. No code fences.
""".strip()


def is_blocked_guide_id(topic_id: str) -> bool:
    tid = (topic_id or "").strip().lower()
    if not tid:
        return True
    if tid in BLOCKED_GUIDE_IDS:
        return True
    return any(tid.startswith(p) for p in BLOCKED_GUIDE_ID_PREFIXES)


def is_non_ramen_slug(safe_name: str, display_name: str = "") -> bool:
    blob = f"{safe_name} {display_name}".lower()
    return any(m in blob for m in NON_RAMEN_SLUG_MARKERS)


def has_real_shop_data(*, lat, lng, address: str) -> bool:
    """Require usable map coordinates and a real address string."""
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return False
    if abs(lat_f) < 0.01 or abs(lng_f) < 0.01:
        return False
    # Rough Japan bounding box (plus a little margin).
    if not (20.0 <= lat_f <= 46.5 and 122.0 <= lng_f <= 154.0):
        return False
    addr = (address or "").strip()
    return len(addr) >= 8


def strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```(?:markdown|yaml)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())
    return text.replace("## yaml", "").strip()


def parse_frontmatter_body(raw: str) -> tuple[dict[str, str], str]:
    raw = strip_code_fences(raw)
    m = FM_SPLIT.match(raw)
    if not m:
        return {}, raw
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, m.group(2).strip()


def hangul_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(HANGUL_RE.findall(text)) / max(len(text), 1)


def extract_h2_headings(body: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+)$", body or "", re.M)]


def find_banned_phrases(text: str) -> list[str]:
    low = (text or "").lower()
    return [p for p in BANNED_PHRASES if p.lower() in low]


def min_chars_for(*, kind: str, sibling_exists: bool = False) -> int:
    if sibling_exists:
        return SIBLING_FILL_MIN_CHARS
    return GUIDE_MIN_CHARS if kind == "guide" else RAMEN_MIN_CHARS


def quality_issues(
    body: str,
    *,
    kind: str = "guide",
    lang: str = "en",
    min_chars: int | None = None,
) -> list[str]:
    text = (body or "").strip()
    issues: list[str] = []
    floor = min_chars if min_chars is not None else min_chars_for(kind=kind)

    if len(text) < floor:
        issues.append(f"too_short:{len(text)}<{floor}")

    headings = [h.lower() for h in extract_h2_headings(text)]
    if len(headings) < MIN_H2:
        issues.append(f"too_few_sections:{len(headings)}")

    banned_heads = [h for h in headings if h in FORBIDDEN_HEADINGS]
    if len(banned_heads) >= 2:
        issues.append(f"template_headings:{', '.join(banned_heads[:4])}")

    banned = find_banned_phrases(text)
    if banned:
        issues.append(f"banned_phrases:{', '.join(banned[:3])}")

    ratio = hangul_ratio(text)
    if lang == "ko" and ratio < 0.08:
        issues.append(f"ko_too_little_hangul:{ratio:.3f}")
    if lang == "en" and ratio > 0.12:
        issues.append(f"en_too_much_hangul:{ratio:.3f}")

    blob = text.lower()
    if kind == "ramen" and "ramen" not in blob and "라멘" not in blob and "麺" not in text:
        issues.append("not_ramen_related")

    return issues


def validate_generated_markdown(
    raw: str,
    *,
    kind: str,
    lang: str,
    sibling_exists: bool = False,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    meta, body = parse_frontmatter_body(raw)

    if not meta:
        errors.append("missing_frontmatter")
    else:
        for key in ("lang", "title", "summary", "date"):
            if not str(meta.get(key, "")).strip():
                errors.append(f"missing_meta:{key}")
        meta_lang = str(meta.get("lang", "")).strip().lower()
        if meta_lang and meta_lang != lang:
            errors.append(f"lang_mismatch_meta:{meta_lang}!={lang}")
        if kind == "ramen":
            for key in ("shop_name", "address", "lat", "lng"):
                if not str(meta.get(key, "")).strip():
                    errors.append(f"missing_meta:{key}")

    errors.extend(
        quality_issues(
            body,
            kind=kind,
            lang=lang,
            min_chars=min_chars_for(kind=kind, sibling_exists=sibling_exists),
        )
    )
    return (len(errors) == 0), errors
