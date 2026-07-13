"""Generate ramen guide markdown with quality gates + retry."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import os
from datetime import datetime

from dotenv import load_dotenv
from google import genai

from content_quality import (
    GUIDE_MIN_CHARS,
    QUALITY_PROMPT_RULES,
    is_blocked_guide_id,
    strip_code_fences,
    validate_generated_markdown,
)
from topic_queue_csv import resolve as resolve_queue_csv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"
MAX_ATTEMPTS = 3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GUIDE_CONTENT_DIR = os.path.join(BASE_DIR, "app", "content", "guides")


def _emit_pipeline_result(**kwargs):
    try:
        from generation_result import emit_generation_result

        emit_generation_result(**kwargs)
    except ImportError:
        pass


def _guides_csv_path() -> str:
    return resolve_queue_csv("guides", os.path.join(SCRIPT_DIR, "csv", "guides.csv"))


def _sibling_exists(guide_id: str, lang: str) -> bool:
    other = "ko" if lang == "en" else "en"
    return os.path.isfile(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_{other}.md"))


def build_guide_prompt(
    *,
    guide_id: str,
    topic: str,
    lang: str,
    keywords: str,
    feedback: str = "",
) -> str:
    lang_full = "Korean" if lang == "ko" else "English"
    filling = _sibling_exists(guide_id, lang)
    length_hint = (
        f"at least {GUIDE_MIN_CHARS + 1500} characters"
        if filling
        else f"at least {GUIDE_MIN_CHARS} characters"
    )
    today = datetime.now().strftime("%Y-%m-%d")
    feedback_block = f"\n[FIX PREVIOUS FAILURE]\n{feedback}\n" if feedback else ""

    return f"""You are a practical Japan ramen travel editor for OKRamen.
Write in {lang_full} only. Help a visitor decide or complete a ramen trip task.

Topic ID: {guide_id}
Topic: {topic}
Keywords: {keywords or topic}

{QUALITY_PROMPT_RULES}
{feedback_block}
[HARD RULES]
- The guide MUST be useful for ramen travel in Japan (styles, regions, etiquette, queue tips).
- If the topic is mainly cafe/coffee/dessert (not ramen), refuse with only: SKIP_NOT_RAMEN
- Body length: {length_hint}.
- At least 4 ## sections with unique titles for THIS topic.
- Do not invent exact shop hours, yen prices, or Michelin claims.
- End with a short nudge to explore the site map / shop list.

[OUTPUT]
Start with YAML frontmatter (no code fences):

---
lang: {lang}
title: "Catchy SEO title about {topic}"
summary: "One concrete sentence that encourages a useful click"
date: "{today}"
---
(Markdown body)
"""


def generate_guide_article(guide_id, topic, lang, keywords) -> str:
    if is_blocked_guide_id(guide_id):
        return f"⏭️ Blocked guide id: {guide_id}_{lang}"

    if not API_KEY:
        return f"❌ API Key missing: {guide_id}_{lang}"

    client = genai.Client(api_key=API_KEY)
    filename = f"{guide_id}_{lang}.md"
    filepath = os.path.join(GUIDE_CONTENT_DIR, filename)
    filling_sibling = _sibling_exists(guide_id, lang)
    feedback = ""
    last_errors: list[str] = []

    print(f"🚀 [Guide AI] Generating {lang} for: {topic}...")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            prompt = build_guide_prompt(
                guide_id=guide_id,
                topic=topic,
                lang=lang,
                keywords=keywords,
                feedback=feedback,
            )
            response = client.models.generate_content(model=MODEL, contents=prompt)
            content = strip_code_fences(response.text or "")
            if "SKIP_NOT_RAMEN" in content[:80]:
                return f"⏭️ Model refused off-topic: {filename}"

            ok, errors = validate_generated_markdown(
                content,
                kind="guide",
                lang=lang,
                sibling_exists=filling_sibling,
            )
            if not ok:
                last_errors = errors
                feedback = "; ".join(errors)
                print(f"⚠️  quality fail {filename} attempt {attempt}: {feedback}")
                continue

            os.makedirs(GUIDE_CONTENT_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ [Done] {filename}"
        except Exception as e:
            last_errors = [str(e)]
            feedback = str(e)
            print(f"❌ attempt {attempt} {filename}: {e}")

    return f"⛔ Quality failed · not saved: {filename} — {', '.join(last_errors)}"


def _orphan_tasks() -> list[tuple]:
    tasks: list[tuple] = []
    csv_path = _guides_csv_path()
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return tasks

    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            guide_id = (row.get("id") or "").strip()
            if not guide_id or is_blocked_guide_id(guide_id):
                continue
            keywords = (row.get("keywords") or "").strip()
            en_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md")
            ko_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md")
            en_exists = os.path.exists(en_path)
            ko_exists = os.path.exists(ko_path)
            if en_exists and not ko_exists:
                tasks.append((guide_id, row.get("topic_ko") or guide_id, "ko", keywords))
            elif ko_exists and not en_exists:
                tasks.append((guide_id, row.get("topic_en") or guide_id, "en", keywords))
    return tasks


def _batch_missing_tasks(limit: int) -> list[tuple]:
    tasks: list[tuple] = []
    csv_path = _guides_csv_path()
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return tasks
    topics = 0
    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            if topics >= limit:
                break
            guide_id = (row.get("id") or "").strip()
            if not guide_id or is_blocked_guide_id(guide_id):
                continue
            keywords = (row.get("keywords") or "").strip()
            en_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md")
            ko_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md")
            topic_tasks: list[tuple] = []
            if not os.path.exists(en_path):
                topic_tasks.append((guide_id, row.get("topic_en") or guide_id, "en", keywords))
            if not os.path.exists(ko_path):
                topic_tasks.append((guide_id, row.get("topic_ko") or guide_id, "ko", keywords))
            if not topic_tasks:
                continue
            tasks.extend(topic_tasks)
            topics += 1
    return tasks


def _new_topic_tasks(limit: int) -> list[tuple]:
    tasks: list[tuple] = []
    csv_path = _guides_csv_path()
    topics = 0
    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            guide_id = (row.get("id") or "").strip()
            if not guide_id or is_blocked_guide_id(guide_id):
                continue
            en_exists = os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md"))
            ko_exists = os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md"))
            if en_exists or ko_exists:
                continue
            keywords = (row.get("keywords") or "").strip()
            tasks.append((guide_id, row.get("topic_en") or guide_id, "en", keywords))
            tasks.append((guide_id, row.get("topic_ko") or guide_id, "ko", keywords))
            topics += 1
            if topics >= limit:
                break
    return tasks


def _csv_missing_tasks() -> list[tuple]:
    tasks: list[tuple] = []
    csv_path = _guides_csv_path()
    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            guide_id = (row.get("id") or "").strip()
            if not guide_id or is_blocked_guide_id(guide_id):
                continue
            keywords = (row.get("keywords") or "").strip()
            if not os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md")):
                tasks.append((guide_id, row.get("topic_en") or guide_id, "en", keywords))
            if not os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md")):
                tasks.append((guide_id, row.get("topic_ko") or guide_id, "ko", keywords))
    return tasks


def _run_tasks(tasks: list[tuple], *, dry_run: bool) -> None:
    topics = len({t[0] for t in tasks})
    if dry_run:
        print(f"🔔 [dry-run] {len(tasks)} guide file(s)")
        for p in tasks:
            print(f"   {p[0]}_{p[2]}.md")
        _emit_pipeline_result(step="guides", topics=topics, generated=0, skipped=len(tasks))
        return
    if not tasks:
        print("✨ No guide orphans to generate.")
        _emit_pipeline_result(step="guides", topics=0, generated=0)
        return
    print(f"🔔 Generating {len(tasks)} guide file(s)")
    ok = 0
    failed = 0
    skipped = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(generate_guide_article, *p) for p in tasks]
        for fut in concurrent.futures.as_completed(futures):
            result = fut.result()
            print(result)
            if result.startswith("✅"):
                ok += 1
            elif result.startswith("⛔") or result.startswith("❌"):
                failed += 1
            else:
                skipped += 1
    _emit_pipeline_result(
        step="guides",
        topics=topics,
        generated=ok,
        failed=failed,
        skipped=skipped,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate guide markdown. Default: orphans only (en or ko already on disk). "
            "Use --new-topics N or --all-missing --yes for broader runs."
        ),
    )
    parser.add_argument(
        "--batch-missing",
        type=int,
        metavar="N",
        help="Fill missing en/ko for up to N CSV topics (full scan; hub default).",
    )
    parser.add_argument(
        "--new-topics",
        type=int,
        metavar="N",
        help="Create en+ko for up to N CSV topics that have no files yet.",
    )
    parser.add_argument(
        "--all-missing",
        action="store_true",
        help="Backfill every missing file in guides.csv (many API calls).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required with --all-missing.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List targets only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.all_missing:
        if not args.yes:
            n = len(_csv_missing_tasks())
            print(
                f"⛔ Blocked: would generate {n} files. "
                "Use --all-missing --yes to confirm."
            )
            if args.dry_run:
                _run_tasks(_csv_missing_tasks(), dry_run=True)
            return 2
        tasks = _csv_missing_tasks()
        print("⚠️  Mode: all missing from guides.csv")
    elif args.batch_missing is not None:
        tasks = _batch_missing_tasks(args.batch_missing)
        print(f"ℹ️  Mode: batch missing (up to {args.batch_missing} topic(s))")
    elif args.new_topics is not None:
        tasks = _new_topic_tasks(args.new_topics)
        print(f"⚠️  Mode: new topics (limit {args.new_topics})")
    else:
        tasks = _orphan_tasks()
        print("ℹ️  Mode: orphans only (missing en or ko when the other exists).")

    _run_tasks(tasks, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
