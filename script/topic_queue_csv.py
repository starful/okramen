"""Resolve CSV path from okadmin topic bank / pipeline queue (TOPIC_* env)."""
from __future__ import annotations

import os
from pathlib import Path


def _sibling_okadmin_csv(default_path: str, bank_id: str, *, source: str) -> str:
    path = Path(default_path).resolve()
    repo_root = path.parents[2] if len(path.parents) >= 3 else None
    if repo_root is None:
        return ""
    okadmin_root = repo_root.parent / "okadmin"
    site_id = repo_root.name
    bank = okadmin_root / "data" / "topic_banks" / site_id / f"{bank_id}.csv"
    queue = okadmin_root / "data" / "pipeline_queues" / site_id / f"{bank_id}.csv"
    candidates = (bank, queue) if source == "bank" else (queue, bank)
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return ""


def resolve(bank_id: str, default_path: str, *, source: str = "queue") -> str:
    """source: 'queue' (generators) or 'bank' (metadata / fetch_images)."""
    norm = bank_id.upper().replace("-", "_")
    if source == "bank":
        keys = (f"TOPIC_BANK_{norm}", f"TOPIC_QUEUE_{norm}", "TOPIC_QUEUE_CSV")
    else:
        keys = (f"TOPIC_QUEUE_{norm}", "TOPIC_QUEUE_CSV", f"TOPIC_BANK_{norm}")
    for key in keys:
        path = (os.environ.get(key) or "").strip()
        if path and os.path.isfile(path):
            return path
    sibling = _sibling_okadmin_csv(default_path, bank_id, source=source)
    if sibling:
        return sibling
    return default_path
