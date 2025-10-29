#!/usr/bin/env python3
"""
Generate AI prompts for additional resources assigned to each scrum team based on
agile-team/ART_Team_Structure.md. Prompts are saved in the corresponding scrum
team folder as <ComicsName>_<Role>.md and leverage SMART and INVEST frameworks.

Heuristics:
- Team folder mapping prioritizes existing directories (handles minor naming diffs).
- Comics names are chosen deterministically (hash of ART+Team+Role+index) from role-aligned pools,
  with safe fallbacks.
"""
from __future__ import annotations
import hashlib
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
TEAM_DOC = ROOT / "agile-team" / "ART_Team_Structure.md"
ORG_DOC = ROOT / "agile-team" / "SAFe6OrganizationStructure.md"
AGILE_TEAM_DIR = ROOT / "agile-team"


def slug(s: str) -> str:
    s = re.sub(r"[\s/]+", "_", s.strip())
    s = re.sub(r"[^A-Za-z0-9_\-]+", "", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def list_existing_team_dirs() -> List[str]:
    if not AGILE_TEAM_DIR.exists():
        return []
    return [p.name for p in AGILE_TEAM_DIR.iterdir() if p.is_dir() and p.name.startswith("ART")] 


TEAM_DIR_MAP: Dict[str, str] = {
    # ART 1
    "Justice League Command": "ART1_Justice_League_Command",
    "Avengers Interface": "ART1_Avengers_Interface",
    # ART 2
    "X-Men Flight": "ART2_X-Men_Flight",
    "Fantastic Four Navigation": "ART2_Fantastic_Four_Navigation",
    # ART 3 (naming diffs)
    "Teen Titans Network": "ART3_Teen_Titans_Communication",
    "Guardians Communication": "ART3_Guardians_of_the_Network",
    # ART 4 (naming diffs)
    "S.H.I.E.L.D. Defense": "ART4_SHIELD_Security",
    "Watchmen Response": "ART4_Watchmen_Intrusion",
    # ART 5
    "Avengers Intelligence": "ART5_Avengers_Intelligence",
    "Justice League Analytics": "ART5_Justice_League_Analytics",
    # ART 6 (naming diffs)
    "X-Men Swarm": "ART6_X-Men_Coordination",
    "Fantastic Four Intelligence": "ART6_Fantastic_Four_Intelligence",
    # ART 7
    "Avengers Assembly": "ART7_Avengers_Assembly",
    "Justice League Validation": "ART7_Justice_League_Validation",
}


def fuzzy_find_team_dir(art_num: str, team_name: str, existing: List[str]) -> Optional[str]:
    # First try map
    mapped = TEAM_DIR_MAP.get(team_name)
    if mapped and (AGILE_TEAM_DIR / mapped).exists():
        return mapped
    # Then try direct slug
    candidate = f"ART{art_num}_" + slug(team_name)
    if candidate in existing:
        return candidate
    # Fuzzy: find dir starting with ARTn and sharing first two words
    words = [w for w in slug(team_name).split('_') if w]
    for d in existing:
        if not d.startswith(f"ART{art_num}_"):
            continue
        if all(w.lower() in d.lower() for w in words[:2]):
            return d
    # As last resort, allow creating new directory (but prefer existing)
    return candidate


def stable_choice(options: List[str], seed_text: str) -> str:
    if not options:
        return "Agent"
    h = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % len(options)
    return options[idx]


ROLE_NAME_POOLS: List[Tuple[List[str], List[str]]] = [
    # keywords, names
    (["ui", "ux", "frontend", "visual"], ["Spider-Gwen", "Wasp", "Batgirl", "Kitty Pryde", "Domino", "Jubilee"]),
    (["mission", "planning"], ["Captain Marvel", "Starfire", "Nova", "Star Girl"]),
    (["real-time", "realtime", "rt"], ["Quicksilver", "Flash", "Velocity", "Impulse"]),
    (["analytics", "bi", "visualization"], ["Oracle", "Dazzler", "The Question", "Cerebra"]),
    (["monitoring", "observability"], ["Heimdall", "Watcher", "Hawk-Eye", "Sentry"]),
    (["flight", "control"], ["Falcon", "Angel", "Polaris"]),
    (["navigation", "nav"], ["Nightcrawler", "Polaris", "Star-Lord"]),
    (["sensor", "fusion", "integration"], ["Daredevil", "Echo", "Cyborg", "Forge"]),
    (["ai", "ml", "autonomous", "autonomy"], ["Brainiac", "Viv Vision", "Vision", "Machine Man"]),
    (["computer", "vision"], ["Cyclops", "Eye-Boy", "Domino"]),
    (["testing", "qa", "quality"], ["Mockingbird", "Jessica Jones", "Mr. Terrific", "Barbara Gordon"]),
    (["hardware"], ["Ironheart", "Steel", "Blue Beetle", "Cyborg"]),
    (["network", "mesh", "p2p"], ["Spider-Woman", "Silk", "Cable", "Cypher"]),
    (["security", "cyber", "intrusion", "ids"], ["Batwoman", "Nightwatch", "Black Panther", "Oracle"]),
    (["rf", "satellite"], ["Static", "Adam Strange", "Photon"]),
    (["incident", "response"], ["Valkyrie", "Firestorm", "Red Tornado"]),
    (["crypto", "cryptography"], ["Enigma", "Cipher", "Riddler"]),
    (["quantum"], ["Quasar", "Photon", "Spectrum"]),
    (["compliance"], ["She-Hulk", "Daredevil", "The Question"]),
    (["data", "etl", "pipeline", "dba"], ["Forge", "Cable", "Cypher", "Brainiac 5"]),
    (["swarm", "formation", "distributed"], ["Ant-Man", "Wasp", "Multiple Man"]),
    (["integration", "interface"], ["Blue Beetle", "Cyborg", "The Atom"]),
    (["automation"], ["Ultron", "Machine Man", "Vision"]),
    (["validation", "end-to-end"], ["The Tick", "Huntress", "Mockingbird"]),
]

DEFAULT_NAME_POOL = [
    "Nova", "Spectrum", "Stargirl", "Shadowcat", "Raven", "Starfire", "Black Lightning",
]


def pick_comics_name(role_label: str, seed_text: str) -> str:
    rl = role_label.lower()
    for keywords, pool in ROLE_NAME_POOLS:
        if any(k in rl for k in keywords):
            return stable_choice(pool, seed_text)
    return stable_choice(DEFAULT_NAME_POOL, seed_text)


def parse_team_rows(md: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    current_art = None
    for line in md.splitlines():
        art_m = re.match(r"^## \*\*ART\s+(\d+):\s+(.+?)\*\*", line)
        if art_m:
            current_art = art_m.group(1)
            continue
        if not line.startswith("|"):
            continue
        if set(line.strip()) <= set("|- "):
            # header delimiter
            continue
        # Split row
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cols) < 4:
            continue
        team, sm, members, specs = cols[:4]
        # Remove ** ** around team
        team = re.sub(r"^\*\*(.+?)\*\*$", r"\1", team)
        if team.lower() == "team" and sm.lower() == "scrum master":
            continue
        rows.append({
            "art": current_art or "",
            "team": team,
            "scrum_master": sm,
            "members": members,
            "specializations": specs,
        })
    return rows


def parse_member_items(members_str: str) -> List[Tuple[int, str]]:
    items: List[Tuple[int, str]] = []
    parts = [p.strip() for p in members_str.split(',') if p.strip()]
    for p in parts:
        m = re.match(r"^(\d+)\s+(.*)$", p)
        if not m:
            continue
        cnt = int(m.group(1))
        role = m.group(2).strip()
        # Normalize plurals like Engineers -> Engineer
        role = re.sub(r"\bEngineers\b", "Engineer", role)
        role = re.sub(r"\bDevelopers\b", "Developer", role)
        role = re.sub(r"\bScientists\b", "Scientist", role)
        role = re.sub(r"\bAnalysts\b", "Analyst", role)
        items.append((cnt, role))
    return items


def build_prompt(name: str, role: str, team: str, art_label: str, specs: str) -> str:
    header = f"# {name} — {role} | {team} ({art_label})\n"
    smart = f"""
## SMART mission
- Specific: Deliver high-quality outcomes as {role} for {team}, aligned to backlog priorities and integration needs.
- Measurable: Complete committed work each sprint; meet KPIs for this role; contribute to PI objectives.
- Achievable: Leverage team capabilities and tooling; escalate blockers early; collaborate with the Scrum Master and Architect.
- Relevant: Directly advances {team}'s specializations ({specs or 'core capabilities'}) within {art_label}.
- Time-bound: Operate on a two-week sprint cadence with daily reporting and PI boundary commitments.
""".strip()

    invest = f"""
## INVEST working story
As {name} ({role}), I will decompose work into small, testable tasks that deliver value for {team} and can be estimated and negotiated with stakeholders.
- Independent: Tasks minimize cross-team blocking; dependencies are identified early.
- Negotiable: Collaborate with Product and Architecture to refine scope and acceptance.
- Valuable: Outcomes enhance {team}'s capabilities ({specs}).
- Estimable: Break down into story-sized increments with clear DoR/DoD.
- Small: Fit within a single sprint where possible.
- Testable: Define objective acceptance criteria and tests.
""".strip()

    kpis = f"""
## KPIs
- Throughput and predictability (stories completed vs. committed)
- Quality (defect rate/rework related to {role})
- Flow (cycle time, WIP limits respected)
- Integration success (tests passed at required level)
- Stakeholder feedback (demo outcomes)
""".strip()

    dod = f"""
## Definition of Done
- Meets acceptance criteria and passes unit/integration/system tests as applicable
- Integrated with dependent components and documented
- Evidence and documentation updated (including compliance if required)
""".strip()

    acceptance = f"""
## Acceptance criteria
- Role-specific responsibilities delivered for this sprint (per backlog items)
- No critical defects; KPI thresholds achieved
- Integration points satisfied; demo acceptance recorded
""".strip()

    ops = """
## Operating cadence
- Daily standup, sprint planning/review/retro
- Scrum of Scrums or ART sync when relevant
- Participation in PI events and system demos
""".strip()

    return "\n\n".join([header, smart, invest, kpis, ops, dod, acceptance]) + "\n"


def main() -> None:
    if not TEAM_DOC.exists():
        raise SystemExit(f"Missing team structure doc: {TEAM_DOC}")
    team_md = TEAM_DOC.read_text(encoding="utf-8")
    rows = parse_team_rows(team_md)
    if not rows:
        raise SystemExit("No team rows parsed from ART_Team_Structure.md")

    existing_dirs = list_existing_team_dirs()
    created_files = 0

    for row in rows:
        art = row["art"] or "?"
        team = row["team"]
        specs = row["specializations"]
        # Find team directory
        team_dir_name = fuzzy_find_team_dir(art, team, existing_dirs)
        team_dir = AGILE_TEAM_DIR / team_dir_name
        team_dir.mkdir(parents=True, exist_ok=True)

        members = parse_member_items(row["members"])
        idx_map: Dict[str, int] = {}
        for count, role_label in members:
            for i in range(count):
                idx_map[role_label] = idx_map.get(role_label, 0) + 1
                seed = f"ART{art}|{team}|{role_label}|{idx_map[role_label]}"
                comics_name = pick_comics_name(role_label, seed)
                file_role = slug(role_label.replace('/', ' or '))
                file_name = f"{slug(comics_name)}_{file_role}.md"
                content = build_prompt(comics_name, role_label, team, f"ART {art}", specs)
                (team_dir / file_name).write_text(content, encoding="utf-8")
                created_files += 1

    print(f"Generated {created_files} additional resource prompts in team folders")


if __name__ == "__main__":
    main()
