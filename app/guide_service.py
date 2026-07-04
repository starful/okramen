import glob
import os
import re

import frontmatter
import markdown

try:
    from .content_new import enrich_item
except ImportError:
    from content_new import enrich_item

DEFAULT_GUIDE_PUBLISHED = "2026-01-01"
MARKDOWN_EXTENSIONS = ["tables", "fenced_code"]
UNSPLASH_GUIDE_IMAGES = [
    "https://images.unsplash.com/photo-1552611052-33e04de081de?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1555126634-323283e090fa?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511910849309-0dffb8785146?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1534604973900-c43ab4c2e0ab?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1526318896980-cf78c088247c?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1503764654157-72d979d9af2f?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1553621042-f6e147245754?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1467003909585-2f8a72700288?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1506368249639-73a05d6f6488?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1525755662778-989d0524087e?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1591814441348-73546747d96a?q=80&w=800&auto=format&fit=crop",
]


def _read_guide_summaries(guide_dir: str, logger=None) -> list[dict]:
    all_raw = []
    files = glob.glob(os.path.join(guide_dir, "*.md"))
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
        except (OSError, ValueError) as exc:
            if logger is not None:
                logger.warning("Failed to parse guide file %s: %s", fpath, exc)
            continue

        all_raw.append(
            {
                "base_id": os.path.basename(fpath).rsplit("_", 1)[0],
                "lang": "en" if "_en.md" in fpath else "ko",
                "full_id": os.path.basename(fpath).replace(".md", ""),
                "title": post.get("title", "Guide"),
                "summary": post.get("summary", ""),
                "published": str(post.get("date", DEFAULT_GUIDE_PUBLISHED)),
            }
        )
    return all_raw


def _guide_image_map(guides: list[dict]) -> dict[str, str]:
    ref_en = sorted(
        [g for g in guides if g["lang"] == "en"],
        key=lambda x: x["published"],
        reverse=True,
    )
    return {
        guide["base_id"]: UNSPLASH_GUIDE_IMAGES[i % len(UNSPLASH_GUIDE_IMAGES)]
        for i, guide in enumerate(ref_en)
    }


def load_guides(guide_dir: str, logger=None) -> dict[str, list[dict]]:
    if not os.path.exists(guide_dir):
        if logger is not None:
            logger.warning("Guide directory does not exist: %s", guide_dir)
        return {"en": [], "ko": []}

    all_raw = _read_guide_summaries(guide_dir, logger=logger)
    id_to_img = _guide_image_map(all_raw)
    default_thumb = UNSPLASH_GUIDE_IMAGES[0]

    new_guides = {"en": [], "ko": []}
    for guide in all_raw:
        new_guides[guide["lang"]].append(
            enrich_item(
                {
                    "id": guide["full_id"],
                    "title": guide["title"],
                    "summary": guide["summary"],
                    "thumbnail": id_to_img.get(guide["base_id"], default_thumb),
                    "published": guide["published"],
                }
            )
        )

    for lang in ("en", "ko"):
        new_guides[lang].sort(key=lambda x: x["published"], reverse=True)
    return new_guides


def _clean_markdown(raw_text: str) -> str:
    raw_text = raw_text.strip()
    raw_text = re.sub(r"^```[a-z]*\n", "", raw_text)
    raw_text = re.sub(r"\n```$", "", raw_text)
    raw_text = re.sub(r"^(##\s*)?yaml\n", "", raw_text, flags=re.IGNORECASE)
    if "---" in raw_text and not raw_text.startswith("---"):
        raw_text = "---" + raw_text.split("---", 1)[1]
    return raw_text


def guide_thumbnail_for_id(guide_dir: str, guide_id: str, logger=None) -> str:
    base_id = guide_id.rsplit("_", 1)[0]
    summaries = _read_guide_summaries(guide_dir, logger=logger)
    return _guide_image_map(summaries).get(base_id, UNSPLASH_GUIDE_IMAGES[0])


def load_guide_post(guide_dir: str, guide_id: str, logger=None):
    md_path = os.path.join(guide_dir, f"{guide_id}.md")
    if not os.path.exists(md_path):
        return None

    with open(md_path, "r", encoding="utf-8") as f:
        raw_text = _clean_markdown(f.read())

    post = frontmatter.loads(raw_text)
    post["id"] = guide_id
    post["thumbnail"] = guide_thumbnail_for_id(guide_dir, guide_id, logger=logger)
    return post


def render_guide_content(post) -> str:
    return markdown.markdown(post.content, extensions=MARKDOWN_EXTENSIONS)
