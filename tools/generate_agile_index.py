#!/usr/bin/env python3
"""
Generate a top-level index README for agile-team/, grouping all teams by ART and
linking to each team's README.md.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
AGILE = ROOT / "agile-team"
ORG = AGILE / "SAFe6OrganizationStructure.md"


def parse_art_names(text: str) -> Dict[str, str]:
    arts: Dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^### \*\*ART\s+(\d+):\s+(.+?)\*\*", line)
        if m:
            arts[m.group(1)] = m.group(2).strip()
    return arts


def collect_teams() -> Tuple[List[Tuple[str, str, str]], List[Tuple[str, str]]]:
    """Return (art_teams, mgmt_dirs) where:
    - art_teams: list of (art_num, team_dir_name, team_title)
    - mgmt_dirs: list of (dir_name, title) for Portfolio/LargeSolution
    """
    art_items: List[Tuple[str, str, str]] = []
    mgmt: List[Tuple[str, str]] = []
    for p in AGILE.iterdir():
        if not p.is_dir() or not p.name.startswith("ART"):
            if p.name in ("Portfolio", "LargeSolution"):
                title = p.name
                readme = p / "README.md"
                if readme.exists():
                    try:
                        for line in readme.read_text(encoding="utf-8", errors="ignore").splitlines():
                            h = re.match(r"^#\s+(.+)$", line.strip())
                            if h:
                                title = h.group(1).strip()
                                break
                    except Exception:
                        pass
                mgmt.append((p.name, title))
            continue
        m = re.match(r"^ART(\d+)_", p.name)
        if not m:
            continue
        art_num = m.group(1)
        # Prefer title from team's README.md first heading
        title = p.name
        readme = p / "README.md"
        if readme.exists():
            try:
                for line in readme.read_text(encoding="utf-8", errors="ignore").splitlines():
                    h = re.match(r"^#\s+(.+)$", line.strip())
                    if h:
                        title = h.group(1).strip()
                        break
            except Exception:
                pass
        art_items.append((art_num, p.name, title))
    # Sort by ART number then title
    art_items.sort(key=lambda t: (int(t[0]), t[2].lower()))
    mgmt.sort(key=lambda t: t[1].lower())
    return art_items, mgmt


def build_index(art_names: Dict[str, str], teams: List[Tuple[str, str, str]]) -> str:
    lines: List[str] = ["# Agile Release Trains (Index)", ""]
    current_art = None
    for art_num, dir_name, display in teams:
        if current_art != art_num:
            current_art = art_num
            art_label = art_names.get(art_num, "")
            heading = f"## ART {art_num}: {art_label}" if art_label else f"## ART {art_num}"
            lines.extend([heading, ""])
        # Link to team folder README if present; else to folder
        team_readme = f"{dir_name}/README.md"
        if not (AGILE / dir_name / "README.md").exists():
            team_readme = f"{dir_name}"
        lines.append(f"- [{display}]({team_readme})")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if not AGILE.exists():
        raise SystemExit(f"Missing directory: {AGILE}")
    art_names: Dict[str, str] = {}
    if ORG.exists():
        art_names = parse_art_names(ORG.read_text(encoding="utf-8"))
    art_teams, mgmt = collect_teams()
    content_lines: List[str] = ["# Agile Release Trains (Index)", ""]
    # Management sections first if present
    if mgmt:
        for dname, title in mgmt:
            content_lines.append(f"## {title}")
            content_lines.append("")
            content_lines.append(f"- [{title}]({dname}/README.md)")
            content_lines.append("")
    content_lines.append(build_index(art_names, art_teams))
    content = "\n".join(content_lines).rstrip() + "\n"
    (AGILE / "README.md").write_text(content, encoding="utf-8")
    print(f"Wrote {AGILE/'README.md'} with {len(art_teams)} teams across {len(set(a for a,_,_ in art_teams))} ARTs")


if __name__ == "__main__":
    main()
