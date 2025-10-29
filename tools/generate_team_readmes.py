#!/usr/bin/env python3
"""
Generate README.md in each agile-team/ART* directory, listing all available role
prompts (Markdown files) in that team folder for quick navigation.

Rules:
- Include all .md files in the folder except README.md
- Use the first Markdown heading (# ...) from each file as the link title if available,
  otherwise use the filename stem.
- Sort entries alphabetically by title.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
AGILE = ROOT / "agile-team"


def get_title_from_file(path: Path) -> str:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return path.stem
    for line in txt.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return path.stem


def folder_title(name: str) -> str:
    # Example: ART2_X-Force_Propulsion_Electronic_Speed_Controller_-_ESC -> ART2: X-Force Propulsion Electronic Speed Controller - ESC
    if name.startswith("ART"):
        parts = name.split('_', 1)
        if len(parts) == 2:
            art, rest = parts
            rest = rest.replace('_', ' ')
            rest = re.sub(r"\s+-\s+", " - ", rest)
            return f"{art}: {rest}"
    return name.replace('_', ' ')


def build_readme(team_dir: Path, entries: List[Tuple[str, str]]) -> str:
    title = folder_title(team_dir.name)
    lines = [f"# {title}", "", "## Role prompts", ""]
    for display, rel in entries:
        lines.append(f"- [{display}]({rel})")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if not AGILE.exists():
        raise SystemExit(f"Missing agile-team directory: {AGILE}")
    count = 0
    team_dirs = [p for p in AGILE.iterdir() if p.is_dir() and (p.name.startswith("ART") or p.name in ("Portfolio", "LargeSolution"))]
    for team_dir in sorted(team_dirs, key=lambda p: p.name):
        md_files = [p for p in team_dir.glob("*.md") if p.name.lower() != "readme.md"]
        if not md_files:
            # Skip empty folders
            continue
        entries: List[Tuple[str, str]] = []
        for f in md_files:
            title = get_title_from_file(f)
            entries.append((title, f.name))
        entries.sort(key=lambda x: x[0].lower())
        readme = build_readme(team_dir, entries)
        (team_dir / "README.md").write_text(readme, encoding="utf-8")
        count += 1
    print(f"Generated README.md for {count} team folders")


if __name__ == "__main__":
    main()
