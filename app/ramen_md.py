"""Ramen markdown: tolerate missing closing '---' before the first markdown heading."""

from __future__ import annotations

import re

import frontmatter
import yaml


def clean_ramen_raw_text(raw_text: str) -> str:
    raw_text = raw_text.strip()
    raw_text = re.sub(r"^```[a-z]*\n", "", raw_text)
    raw_text = re.sub(r"\n```$", "", raw_text)
    raw_text = re.sub(r"^(##\s*)?yaml\n", "", raw_text, flags=re.IGNORECASE)
    if "---" in raw_text and not raw_text.startswith("---"):
        raw_text = "---" + raw_text.split("---", 1)[1]
    return raw_text


def _split_open_frontmatter(lines: list[str]) -> tuple[str, str] | None:
    """If the first line opens frontmatter but there is no closing ---, split at first ATX heading."""
    if not lines or lines[0].strip() != "---":
        return None
    close_idx: int | None = None
    heading_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break
        if re.match(r"^#{1,6}\s", lines[i]):
            heading_idx = i
            break
    if close_idx is not None:
        yaml_block = "\n".join(lines[1:close_idx])
        body = "\n".join(lines[close_idx + 1 :])
        return yaml_block, body
    if heading_idx is not None:
        yaml_lines = lines[1:heading_idx]
        while yaml_lines and not yaml_lines[-1].strip():
            yaml_lines.pop()
        yaml_block = "\n".join(yaml_lines)
        body = "\n".join(lines[heading_idx:])
        return yaml_block, body
    return None


def loads_ramen_post(raw_text: str) -> frontmatter.Post:
    cleaned = clean_ramen_raw_text(raw_text)
    post = frontmatter.loads(cleaned)
    if post.get("title"):
        return post
    lines = cleaned.splitlines()
    split = _split_open_frontmatter(lines)
    if not split:
        return post
    yaml_block, body = split
    try:
        meta = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        return post
    if not isinstance(meta, dict):
        return post
    return frontmatter.Post(body, **meta)
