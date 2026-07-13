"""Tests for okramen content_quality gates."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))

from content_quality import (  # noqa: E402
    has_real_shop_data,
    is_blocked_guide_id,
    is_non_ramen_slug,
    quality_issues,
    validate_generated_markdown,
)


def test_blocked_guide_ids():
    assert is_blocked_guide_id("guide_seed_001")
    assert is_blocked_guide_id("guide_expand_003")
    assert not is_blocked_guide_id("late_night_culture")


def test_non_ramen_slug():
    assert is_non_ramen_slug("kobe_harborland_cafe", "Kobe Harborland Cafe")
    assert is_non_ramen_slug("sendai_ichibancho_latte")
    assert not is_non_ramen_slug("ichiran_shinjuku", "Ichiran Shinjuku")


def test_has_real_shop_data():
    assert has_real_shop_data(lat=35.6909, lng=139.7018, address="Tokyo, Shinjuku")
    assert not has_real_shop_data(lat=0, lng=0, address="Tokyo, Shinjuku")
    assert not has_real_shop_data(lat=35.6, lng=139.7, address="x")
    assert not has_real_shop_data(lat="bad", lng=139.7, address="Tokyo, Shinjuku")


def test_quality_rejects_template_headings_and_short_body():
    body = """
## What changes
short
## When this tends to work
short
## Practical takeaway
short
"""
    issues = quality_issues(body, kind="guide", lang="en", min_chars=4000)
    assert any(i.startswith("too_short") for i in issues)
    assert any(i.startswith("template_headings") for i in issues)


def test_validate_ramen_markdown_ok():
    body = "라멘 " * 900 + "\n\n## 개요\n" + ("내용 " * 200) + "\n## 주문\n" + ("팁 " * 200) + "\n## 접근\n" + ("역 " * 200)
    raw = f"""---
lang: ko
title: "테스트 라멘"
summary: "한 줄 요약입니다"
date: "2026-07-13"
shop_name: "테스트"
address: "Tokyo, Shinjuku"
lat: 35.69
lng: 139.70
---

{body}
"""
    ok, errors = validate_generated_markdown(raw, kind="ramen", lang="ko")
    assert ok, errors
