import re
import urllib.parse


def truncate_text(value, max_len):
    text = " ".join(str(value or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def social_image_url(site_url: str, base_id: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]", "", base_id.lower())
    return f"{site_url}/social/{safe}.jpg"


def og_image_context(site_url: str, base_id: str) -> dict:
    og_image_abs = social_image_url(site_url, base_id)
    return {
        "og_image_abs": og_image_abs,
        "og_image_width": 1200,
        "og_image_height": 630,
    }


def card_path(ramen_id: str) -> str:
    return f"/card/{ramen_id}"


def linkedin_inspector_url(page_url: str) -> str:
    return f"https://www.linkedin.com/post-inspector/inspect/{urllib.parse.quote(page_url, safe='')}"


def share_context(site_url: str, slug: str, title: str, lang: str, page_path: str, base_id: str = "") -> dict:
    share_url = f"{site_url}{page_path}"
    share_url_x = f"{site_url}{card_path(slug)}"
    if lang == "ko":
        share_tweet = f"{title} — OKRamen"
    else:
        share_tweet = f"{title} — Japan ramen guide on OKRamen"
    return {
        "share_id": slug,
        "share_url": share_url,
        "share_url_x": share_url_x,
        "share_tweet": share_tweet,
        "share_lang": lang if lang in ("en", "ko") else "en",
        "og_page_url": share_url,
        "linkedin_inspector_url": linkedin_inspector_url(share_url),
    }


def attach_seo_fields(post, suffix):
    """Set SEO title/description while honoring explicit frontmatter overrides."""
    title = str(post.get("title", "")).strip()
    summary = str(post.get("summary", "")).strip()
    lang = str(post.get("lang", "en") or "en").lower()
    is_ramen_page = "Japan Guide" in suffix

    override_title = str(post.get("seo_title", "") or "").strip()
    override_desc = str(post.get("seo_description", "") or "").strip()
    shop_name = str(post.get("shop_name") or "").strip()
    region = ""
    if is_ramen_page and post.get("address"):
        region = str(post.get("address", "")).split(",")[0].strip()

    if lang == "ko":
        hook = "지도·영업·추천 메뉴" if is_ramen_page else "핵심만 정리한 가이드"
        tail = (
            " OKRamen 지도에서 위치·영업·추천 메뉴를 바로 확인하세요."
            if is_ramen_page
            else " OKRamen에서 팁과 링크만 골라 읽고 일정에 넣으세요."
        )
        if is_ramen_page and shop_name and not override_title:
            default_title = truncate_text(f"{shop_name} | {region} 라멘 가이드 | OKRamen", 60)
        else:
            default_title = (
                truncate_text(f"{title} | {hook} | OKRamen", 60)
                if title
                else truncate_text(suffix, 60)
            )
    else:
        hook = "map, hours & what to order" if is_ramen_page else "plain-English tips"
        tail = (
            " Open OKRamen for the map, hours, and what to order before you go."
            if is_ramen_page
            else " Skim OKRamen for maps, ordering tips, and links before your trip."
        )
        if is_ramen_page and shop_name and not override_title:
            default_title = truncate_text(f"{shop_name} | {region} ramen guide | OKRamen", 60)
        else:
            default_title = (
                truncate_text(f"{title} | {hook} | OKRamen", 60)
                if title
                else truncate_text(suffix, 60)
            )

    post["seo_title"] = truncate_text(override_title, 60) if override_title else default_title

    if override_desc:
        post["seo_description"] = truncate_text(override_desc, 160)
    elif is_ramen_page and post.get("one_liner"):
        post["seo_description"] = truncate_text(
            f"{post['one_liner']}{tail if lang == 'en' else ' OKRamen 지도에서 위치·영업·추천 메뉴를 확인하세요.'}",
            155,
        )
    else:
        core = (summary or title).strip()
        post["seo_description"] = truncate_text(f"{core}{tail}", 155)
    return post
