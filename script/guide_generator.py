import argparse
import os
import csv
import re
import sys
import concurrent.futures
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GUIDE_CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content', 'guides')


def clean_ai_response(text):
    """AI 출력물에서 불필요한 태그 제거"""
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text.strip()


def generate_guide_article(guide_id, topic, lang, keywords):
    if not API_KEY:
        print("❌ API Key missing")
        return

    client = genai.Client(api_key=API_KEY)
    model_name = 'gemini-2.5-flash'

    print(f"🚀 [Guide AI] Generating {lang} article for: {topic}...")

    prompt = f"""
    You are a professional travel blogger and Japanese food expert. 
    Write a high-quality, SEO-optimized educational guide about Japanese Ramen.
    
    [Topic]
    - Subject: {topic}
    - Language: {lang}
    - SEO Keywords: {keywords}

    [Output Format - STRICT]
    ---
    lang: {lang}
    title: "Write a catchy, SEO-friendly title in {lang}"
    date: "{datetime.now().strftime('%Y-%m-%d')}"
    summary: "Write a 2-sentence summary that encourages clicks (single line)."
    ---

    [Article Requirements]
    1. Introduction: Hook the reader.
    2. Main Content: Use descriptive H2 and H3 headers.
    3. Formatting: Use bullet points, bold text for key terms.
    4. Length: Minimum 4,000 characters for deep SEO.
    5. Conclusion: End with a link back to our map to find a shop.

    IMPORTANT: DO NOT use markdown code blocks (```). Start directly with '---'.
    """

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        final_text = clean_ai_response(response.text)

        os.makedirs(GUIDE_CONTENT_DIR, exist_ok=True)
        filename = f"{guide_id}_{lang}.md"
        with open(os.path.join(GUIDE_CONTENT_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(final_text)

        print(f"✅ [Done] {filename}")
    except Exception as e:
        print(f"❌ [Failed] {guide_id}: {e}")


def _orphan_tasks() -> list[tuple]:
    """Only the missing lang when the other already exists on disk."""
    tasks: list[tuple] = []
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'guides.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return tasks

    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        for row in csv.DictReader(file):
            guide_id = (row.get('id') or '').strip()
            if not guide_id:
                continue
            keywords = (row.get('keywords') or '').strip()
            en_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md")
            ko_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md")
            en_exists = os.path.exists(en_path)
            ko_exists = os.path.exists(ko_path)
            if en_exists and not ko_exists:
                tasks.append((guide_id, row.get('topic_ko') or guide_id, 'ko', keywords))
            elif ko_exists and not en_exists:
                tasks.append((guide_id, row.get('topic_en') or guide_id, 'en', keywords))

    return tasks


def _batch_missing_tasks(limit: int) -> list[tuple]:
    """Up to `limit` CSV topics with any missing en/ko (full CSV scan)."""
    tasks: list[tuple] = []
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'guides.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return tasks
    topics = 0
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        for row in csv.DictReader(file):
            if topics >= limit:
                break
            guide_id = (row.get('id') or '').strip()
            if not guide_id:
                continue
            keywords = (row.get('keywords') or '').strip()
            en_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md")
            ko_path = os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md")
            topic_tasks: list[tuple] = []
            if not os.path.exists(en_path):
                topic_tasks.append((guide_id, row.get('topic_en') or guide_id, 'en', keywords))
            if not os.path.exists(ko_path):
                topic_tasks.append((guide_id, row.get('topic_ko') or guide_id, 'ko', keywords))
            if not topic_tasks:
                continue
            tasks.extend(topic_tasks)
            topics += 1
    return tasks


def _new_topic_tasks(limit: int) -> list[tuple]:
    """CSV rows with neither en nor ko (opt-in; can create many files)."""
    tasks: list[tuple] = []
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'guides.csv')
    topics = 0
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        for row in csv.DictReader(file):
            guide_id = (row.get('id') or '').strip()
            if not guide_id:
                continue
            en_exists = os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md"))
            ko_exists = os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md"))
            if en_exists or ko_exists:
                continue
            keywords = (row.get('keywords') or '').strip()
            tasks.append((guide_id, row.get('topic_en') or guide_id, 'en', keywords))
            tasks.append((guide_id, row.get('topic_ko') or guide_id, 'ko', keywords))
            topics += 1
            if topics >= limit:
                break
    return tasks


def _csv_missing_tasks() -> list[tuple]:
    """Every missing en/ko from guides.csv (expensive; opt-in)."""
    tasks: list[tuple] = []
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'guides.csv')
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        for row in csv.DictReader(file):
            guide_id = (row.get('id') or '').strip()
            if not guide_id:
                continue
            keywords = (row.get('keywords') or '').strip()
            if not os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md")):
                tasks.append((guide_id, row.get('topic_en') or guide_id, 'en', keywords))
            if not os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md")):
                tasks.append((guide_id, row.get('topic_ko') or guide_id, 'ko', keywords))
    return tasks


def _run_tasks(tasks: list[tuple], *, dry_run: bool) -> None:
    if dry_run:
        print(f"🔔 [dry-run] {len(tasks)} guide file(s)")
        for p in tasks:
            print(f"   {p[0]}_{p[2]}.md")
        return
    if not tasks:
        print("✨ No guide orphans to generate.")
        return
    print(f"🔔 Generating {len(tasks)} guide file(s)")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(lambda p: generate_guide_article(*p), tasks)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate guide markdown. Default: orphans only (en or ko already on disk). "
            "Use --new-topics N or --all-missing --yes for broader runs."
        ),
    )
    parser.add_argument(
        '--batch-missing',
        type=int,
        metavar='N',
        help='Fill missing en/ko for up to N CSV topics (full scan; hub default).',
    )
    parser.add_argument(
        '--new-topics',
        type=int,
        metavar='N',
        help='Create en+ko for up to N CSV topics that have no files yet.',
    )
    parser.add_argument(
        '--all-missing',
        action='store_true',
        help='Backfill every missing file in guides.csv (many API calls).',
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Required with --all-missing.',
    )
    parser.add_argument('--dry-run', action='store_true', help='List targets only.')
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
