#!/usr/bin/env python3
"""
Parse agile-team/Role-extended-prompt.md and generate AI prompts for each resource
not already covered in team-level generators. Specifically handles:
- Portfolio Level table (Zeus, Athena, Hermes)
- Large Solution Level table (M, Q, Moneypenny)

Outputs are placed in:
- agile-team/Portfolio/<Name>_<Role>.md
- agile-team/LargeSolution/<Name>_<Role>.md

Prompts include SMART and INVEST frameworks, KPIs, cadence, DoD, acceptance criteria,
and context from the table columns.
"""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "agile-team" / "Role-extended-prompt.md"


def slug(s: str) -> str:
    import re as _re
    s = _re.sub(r"[\s/]+", "_", s.strip())
    s = _re.sub(r"[^A-Za-z0-9_\-]+", "", s)
    s = _re.sub(r"_+", "_", s)
    return s.strip("_")


def parse_markdown_table(lines: list[str], start_idx: int) -> tuple[list[dict[str, str]], int]:
    """Parse a GitHub-flavored Markdown table starting at start_idx.
    Returns (rows, next_index_after_table).
    """
    headers = [h.strip() for h in lines[start_idx].strip().strip('|').split('|')]
    i = start_idx + 1
    # skip delimiter
    while i < len(lines) and set(lines[i].strip()) <= set("|- :"):
        i += 1
    rows: list[dict[str, str]] = []
    while i < len(lines):
        line = lines[i]
        if not line.strip().startswith('|'):
            break
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cols) < len(headers):
            break
        row = dict(zip(headers, cols))
        rows.append(row)
        i += 1
    return rows, i


def render_prompt(name: str, role: str, skills: str, responsibilities: str,
                  straight_line: str, dotted_line: str, relationships: str,
                  scope: str) -> str:
    header = f"# {name} — {role} | {scope}\n"
    ctx = f"""
## Role context
- Skills: {skills or 'N/A'}
- Responsibilities: {responsibilities or 'N/A'}
- Straight line reports: {straight_line or 'N/A'}
- Dotted line reports: {dotted_line or 'N/A'}
- Key relationships: {relationships or 'N/A'}
""".strip()

    smart = f"""
## SMART mission
- Specific: Deliver {role.lower()} outcomes for {scope}, aligned with strategy and governance responsibilities.
- Measurable: Meet KPIs and review checkpoints each sprint/PI; close dependencies and decisions on time.
- Achievable: Leverage relationships ({relationships or 'stakeholders'}) and reporting lines to remove blockers.
- Relevant: Directly advances portfolio/solution objectives and cross-ART alignment.
- Time-bound: Operate on sprint/PI cadence with monthly/quarterly governance reviews.
""".strip()

    invest = f"""
## INVEST leadership story
As {name} ({role}), I will structure initiatives and decisions so that they are independent, negotiable, valuable, estimable, small (incremental), and testable via objective criteria.
- Independent: Decisions minimize unnecessary coupling while respecting guardrails.
- Negotiable: Collaborate with stakeholders to refine scope and options.
- Valuable: Outcomes improve delivery flow, quality, or strategic alignment.
- Estimable: Define milestones and acceptance criteria for progress visibility.
- Small: Deliver change in increments to enable feedback and adaptation.
- Testable: Establish measurable success criteria and leading indicators.
""".strip()

    kpis = """
## KPIs
- Flow and predictability across ARTs (PI objectives met)
- Architectural compliance and runway health
- Risk/impediment resolution lead time
- Stakeholder satisfaction and decision latency
- Cross-team dependency aging and closure rate
""".strip()

    cadence = """
## Operating cadence
- Participate in PI planning, system demos, and governance reviews
- Facilitate or attend Solution/Architecture/Stakeholder syncs as applicable
- Provide regular status, risks, and decisions to stakeholders
""".strip()

    anchors = """
## Cross-team integration anchors
- [GCS ↔ Airborne](#cip-gcs-airborne)
- [Communication ↔ Security](#cip-comm-security)
- [Swarm ↔ Airborne](#cip-swarm-airborne)
- [Data ↔ All Teams](#cip-data-all)
- [Integration ↔ All Teams](#cip-integration-all)
- [Airborne (ESC) ↔ Integration](#cip-esc-integration)
- [Airborne (Gimbal) ↔ GCS & Integration](#cip-gimbal-gcs-integration)
- [Security Auditors ↔ All Teams](#cip-auditors-all)
- [Data & Analytics ↔ Airborne (ESC)](#cip-data-esc)
- [Data & Analytics ↔ Airborne (Gimbal)](#cip-data-gimbal)
""".strip()

    dod = """
## Definition of Done
- Responsibilities executed with evidence (artifacts, decisions, approvals)
- Dependencies resolved or tracked with owners/dates
- Risks addressed with mitigations; stakeholders informed
""".strip()

    acceptance = """
## Acceptance criteria
- Agreed responsibilities for the increment are met
- KPIs within thresholds; stakeholder sign-off recorded
- No critical open risks without mitigation/owner/date
""".strip()

    return "\n\n".join([header, ctx, smart, invest, kpis, anchors, cadence, dod, acceptance]) + "\n"


def write_prompt(scope_dir: Path, name: str, role: str, content: str) -> None:
    scope_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug(name)}_{slug(role.replace(' ', '_'))}.md"
    (scope_dir / filename).write_text(content, encoding="utf-8")


def main() -> None:
    if not DOC.exists():
        raise SystemExit(f"Missing source doc: {DOC}")
    text = DOC.read_text(encoding="utf-8")
    lines = text.splitlines()

    i = 0
    created = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("## **Portfolio Level"):
            # Next non-empty line with '|' starts the table header
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('|'):
                i += 1
            rows, i = parse_markdown_table(lines, i)
            for r in rows:
                name = re.sub(r"^\*\*(.+?)\*\*$", r"\1", r.get('Character','').strip())
                role = r.get('Role','').strip()
                skills = r.get('Skills','').strip()
                resp = r.get('Responsibilities','').strip()
                straight_line = r.get('Straight Line Reports','').strip()
                dotted = r.get('Dotted Line Reports','').strip()
                rel = r.get('Key Relationships','').strip()
                content = render_prompt(name, role, skills, resp, straight_line, dotted, rel, scope='Portfolio')
                write_prompt(ROOT/"agile-team"/"Portfolio", name, role, content)
                created += 1
            continue
        if line.strip().startswith("## **Large Solution Level"):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('|'):
                i += 1
            rows, i = parse_markdown_table(lines, i)
            for r in rows:
                name = re.sub(r"^\*\*(.+?)\*\*$", r"\1", r.get('Character','').strip())
                role = r.get('Role','').strip()
                skills = r.get('Skills','').strip()
                resp = r.get('Responsibilities','').strip()
                straight_line = r.get('Straight Line Reports','').strip()
                dotted = r.get('Dotted Line Reports','').strip()
                rel = r.get('Key Relationships','').strip()
                content = render_prompt(name, role, skills, resp, straight_line, dotted, rel, scope='Large Solution')
                write_prompt(ROOT/"agile-team"/"LargeSolution", name, role, content)
                created += 1
            continue
        i += 1

    print(f"Generated {created} management prompts (Portfolio/Large Solution)")


if __name__ == "__main__":
    main()
