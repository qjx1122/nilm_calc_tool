#!/usr/bin/env python3
"""Generate the four standalone manuals used by the in-app assistant.

Sources are the tracked README, stable design report, profile algorithm design,
and the complete NILM tuning/validation guide. Runtime data and ``tmp/`` are
never read. Use ``--check`` in CI to verify generated files are up to date.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.assistant_docs import GENERATED_DOCUMENTS, build_project_documents  # noqa: E402


def render_documents(root: Path) -> Dict[str, str]:
    """Return generated relative paths and UTF-8 Markdown contents."""
    rendered = {item["id"]: item["content"] for item in build_project_documents(root)}
    return {
        relative_path: rendered[doc_id].rstrip() + "\n"
        for doc_id, _title, _category, relative_path, _summary in GENERATED_DOCUMENTS
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: detected from this script)")
    parser.add_argument("--check", action="store_true", help="check generated files without writing them")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    rendered = render_documents(root)
    stale = []
    for relative_path, content in rendered.items():
        path = root / relative_path
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if args.check:
            if current != content:
                stale.append(relative_path)
                print(f"OUT OF DATE: {relative_path}")
            else:
                print(f"OK: {relative_path} ({len(content)} characters)")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        temporary.replace(path)
        print(f"Generated: {relative_path} ({len(content)} characters)")
    if stale:
        print("Regenerate the listed manuals with: python tools/generate_assistant_docs.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
