import os

import markdown

try:
    from .ramen_md import loads_ramen_post
    from .ramen_practical import apply_practical_fields
except ImportError:
    from ramen_md import loads_ramen_post
    from ramen_practical import apply_practical_fields

MARKDOWN_EXTENSIONS = ["tables", "fenced_code"]


def load_ramen_post(content_dir: str, ramen_id: str):
    md_path = os.path.join(content_dir, f"{ramen_id}.md")
    if not os.path.exists(md_path):
        return None

    with open(md_path, "r", encoding="utf-8") as f:
        post = loads_ramen_post(f.read())

    post["id"] = ramen_id
    categories = post.get("categories")
    if categories is None:
        post["categories"] = []
    elif isinstance(categories, str):
        post["categories"] = [c.strip() for c in categories.split(",")]
    return post


def prepare_ramen_detail_post(content_dir: str, ramen_id: str, thumbnail_with_v):
    post = load_ramen_post(content_dir, ramen_id)
    if post is None:
        return None, ""

    apply_practical_fields(post, ramen_id)
    base_id = ramen_id.rsplit("_", 1)[0]
    cache_v = post.get("date") or post.get("published")
    thumb = post.get("thumbnail") or f"/static/images/{base_id}.jpg"
    post["thumbnail"] = thumbnail_with_v(thumb, cache_v)
    return post, base_id


def prepare_ramen_card_post(content_dir: str, ramen_id: str):
    post = load_ramen_post(content_dir, ramen_id)
    if post is None:
        return None, ""

    apply_practical_fields(post, ramen_id)
    return post, ramen_id.rsplit("_", 1)[0]


def render_ramen_content(post) -> str:
    return markdown.markdown(post.content, extensions=MARKDOWN_EXTENSIONS)
