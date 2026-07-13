#!/usr/bin/env python3
"""AI rewrite for okramen GSC rewrite bucket — short practical EN/KO bodies."""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import frontmatter
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))
from gsc_cleanup_plan import GSC_ZIP, classify, lang_from_stem  # noqa: E402

load_dotenv(ROOT / ".env")

_thread_local = threading.local()
HANGUL = re.compile(r"[\uac00-\ud7a3]")
BILINGUAL_HEADER = re.compile(r"^## .+ / [\uac00-\ud7a3]", re.M)


def clean_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.replace("```markdown", "").replace("```", "").strip()


def get_client(api_key: str):
    if getattr(_thread_local, "client", None) is None:
        from google import genai

        _thread_local.client = genai.Client(api_key=api_key)
    return _thread_local.client


def call_gemini(api_key: str, prompt: str) -> str:
    client = get_client(api_key)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return clean_response(response.text or "")


def strip_leading_yaml_in_body(body: str) -> str:
    text = body.strip()
    while text:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3 and "lang:" in parts[1]:
                text = parts[2].strip()
                continue
            break
        if re.match(r"^lang:\s", text):
            end = re.search(r"\n---\s*\n", text)
            if end:
                text = text[end.end() :].strip()
                continue
            break
        break
    return text


def dump_meta(meta: dict) -> str:
    class Dumper(yaml.SafeDumper):
        pass

    def represent_str(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        if any(c in data for c in ":{}[]#&*!|>'\"%@`"):
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    Dumper.add_representer(str, represent_str)
    return yaml.dump(meta, Dumper=Dumper, allow_unicode=True, sort_keys=False).strip()


def parse_ai_output(raw: str, fallback_meta: dict) -> tuple[dict, str]:
    raw = clean_response(raw)
    meta = dict(fallback_meta)
    if not raw.startswith("---"):
        return meta, strip_leading_yaml_in_body(raw)
    parts = raw.split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else ""
    try:
        post = frontmatter.loads(raw)
        meta.update({k: v for k, v in post.metadata.items() if v is not None and v != ""})
        body = post.content.strip() or body
    except Exception:
        if len(parts) >= 2:
            try:
                loaded = yaml.safe_load(parts[1]) or {}
                if isinstance(loaded, dict):
                    meta.update(loaded)
            except Exception:
                pass
    return meta, strip_leading_yaml_in_body(body)


KEEP_META = (
    "address",
    "lat",
    "lng",
    "categories",
    "date",
    "thumbnail",
    "agoda",
    "lang",
    "shop_name",
)


def merge_meta(old: dict, new: dict, kind: str) -> dict:
    merged = dict(old)
    for k, v in new.items():
        if k in KEEP_META and old.get(k) not in (None, ""):
            merged[k] = old[k]
        elif v is not None and v != "":
            merged[k] = v
    if not merged.get("date"):
        merged["date"] = old.get("date") or datetime.now().strftime("%Y-%m-%d")
    if kind == "ramen":
        for k in ("address", "lat", "lng", "shop_name", "categories", "thumbnail"):
            if old.get(k) not in (None, ""):
                merged[k] = old[k]
    return merged


def sanitize_lang(body: str, lang: str) -> str:
    body = BILINGUAL_HEADER.sub(lambda m: m.group(0).split(" / ")[0], body)
    if lang == "en":
        # drop obvious KO footers left in EN
        body = re.sub(r"(?m)^.*[\uac00-\ud7a3].*$", "", body) if False else body
        # lighter: only strip known KO nav lines
        body = body.replace("가이드 목록으로", "Back to guides")
        body = body.replace("라멘 지도로", "Back to ramen map")
    return body.strip() + "\n"


def write_file(path: Path, meta: dict, body: str) -> None:
    lang = lang_from_stem(path.stem)
    body = strip_leading_yaml_in_body(body)
    body = sanitize_lang(body, lang)
    if lang == "en" and HANGUL.search(body):
        # remove lines that are mostly hangul
        lines = []
        for line in body.splitlines():
            if HANGUL.search(line) and len(re.findall(r"[\uac00-\ud7a3]", line)) > max(8, len(line) // 4):
                continue
            lines.append(line)
        body = "\n".join(lines).strip() + "\n"
    text = f"---\n{dump_meta(meta)}\n---\n\n{body.strip()}\n"
    path.write_text(text, encoding="utf-8")


def ramen_prompt(meta: dict, lang: str, base: str) -> str:
    shop = meta.get("shop_name") or meta.get("title") or base
    addr = meta.get("address") or ""
    cats = meta.get("categories") or []
    if lang == "ko":
        return f"""당신은 일본 라멘 실전 가이드 작가입니다. 아래 가게 페이지를 한국어로 재작성하세요.

규칙:
- 본문 1,800~2,800자 (공백 포함)
- 실용적: 무엇을 시키고, 줄/대기, 위치 팁, 비슷한 대안
- 템플릿 문구/과장/미슐랭 남발 금지
- 헤더는 한국어만 (예: ## 한눈에, ## 맛과 주문, ## 방문 팁). 영어 병기 금지
- 출력은 YAML frontmatter(---) + 마크다운 본문만
- frontmatter에 lang: ko, title, summary, seo_title, seo_description 포함
- 사실: shop={shop}, address={addr}, categories={cats}, slug={base}
"""
    return f"""You are rewriting a Japan ramen shop page for travelers.

Rules:
- Body 1,800–2,800 characters
- Practical: what to order, queue tips, how to get there, nearby alternatives
- No template fluff, no fake Michelin claims
- English-only headings (## Overview, ## What to order, ## Visit tips). No Korean in body or headings
- Output YAML frontmatter (---) + markdown body only
- Include lang: en, title, summary, seo_title, seo_description
- Facts: shop={shop}, address={addr}, categories={cats}, slug={base}
"""


def guide_prompt(meta: dict, lang: str, base: str) -> str:
    title = meta.get("title") or base
    if lang == "ko":
        return f"""일본 라멘 가이드 페이지를 한국어로 재작성하세요. 주제 슬러그: {base}, 기존 제목: {title}

규칙:
- 본문 2,000~3,000자
- 체크리스트 템플릿/양산 톤 금지. 구체적 팁과 예시 가게/지역
- 헤더 한국어만. 영어 병기 금지
- YAML frontmatter + 마크다운만 출력 (lang: ko, title, summary, seo_title, seo_description)
"""
    return f"""Rewrite this Japan ramen guide page in English. Slug: {base}, title hint: {title}

Rules:
- Body 2,000–3,000 characters
- No generic checklist template tone. Specific tips, regions, example shops
- English-only. No Korean characters in body or headings
- Output YAML frontmatter + markdown only (lang: en, title, summary, seo_title, seo_description)
"""


def rewrite_one(path: Path, kind: str, api_key: str) -> str:
    raw = path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    meta = dict(post.metadata)
    lang = lang_from_stem(path.stem)
    base = path.stem.rsplit("_", 1)[0] if path.stem.endswith(("_en", "_ko")) else path.stem
    prompt = ramen_prompt(meta, lang, base) if kind == "ramen" else guide_prompt(meta, lang, base)
    # include a short excerpt of old body for grounding
    prompt += f"\n\nExisting body excerpt (for facts only, do not copy style):\n{post.content[:1200]}\n"
    out = call_gemini(api_key, prompt)
    new_meta, body = parse_ai_output(out, meta)
    new_meta = merge_meta(meta, new_meta, kind)
    new_meta["lang"] = lang
    if len(body) < 800:
        raise RuntimeError(f"body too short ({len(body)})")
    write_file(path, new_meta, body)
    return kind


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--zip", type=Path, default=GSC_ZIP)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.dry_run:
        print("❌ GEMINI_API_KEY missing")
        return 1

    buckets = classify(args.zip)
    rewrite = sorted(buckets["rewrite"], key=lambda t: -t["imp"])
    tasks: list[tuple[str, Path]] = []
    for t in rewrite:
        for f in t["files"]:
            tasks.append((t["kind"], f["path"]))
    if args.limit:
        tasks = tasks[: args.limit]

    print(f"🚀 Rewrite queue: {len(tasks)} files from {len(rewrite)} topics (workers={args.workers})", flush=True)
    if args.dry_run:
        for kind, path in tasks[:20]:
            print(f"  would {kind} {path.name}")
        if len(tasks) > 20:
            print(f"  ... +{len(tasks)-20}")
        return 0

    counts: dict[str, int] = {}
    errors: list[str] = []

    def run(item):
        kind, path = item
        try:
            r = rewrite_one(path, kind, api_key)
            return path.name, r
        except Exception as e:
            return path.name, f"error:{e}"

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(run, t) for t in tasks]
        for i, fut in enumerate(as_completed(futures), 1):
            name, result = fut.result()
            if str(result).startswith("error:"):
                errors.append(f"{name}: {result[6:]}")
                print(f"⚠️  [{i}/{len(tasks)}] {name} — {result[6:]}", flush=True)
            else:
                counts[result] = counts.get(result, 0) + 1
                print(f"✅ [{i}/{len(tasks)}] {name} ({result})", flush=True)

    print("Summary:", counts, flush=True)
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:20]:
            print(" ", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
