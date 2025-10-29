#!/usr/bin/env python3
"""
Generate AI agent prompt files from agile-team/SAFe6OrganizationStructure.md.

Output: agile-team/<team_dir>/<Name>_<Role>.md
 - team_dir is derived from ART and Team name when available, otherwise from top-level scope
 - Uses SMART and INVEST frameworks in the prompt content

Assumptions:
 - Markdown format follows the existing structure with headers and bold/italic markers
 - Roles appear as: **Name** - *Role*
 - Details follow as list items beginning with - **Skills**:, - **Responsibilities**:, - **Relationships**:, - **Team**:
 - Optional - **Data dependencies**: is supported
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "agile-team" / "SAFe6OrganizationStructure.md"


def slugify(text: str) -> str:
    text = re.sub(r"[\s/]+", "_", text.strip())
    text = re.sub(r"[^A-Za-z0-9_\-]+", "", text)
    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


class Agent:
    def __init__(self, name: str, role: str, scope: str, team_name: Optional[str], art_label: Optional[str]):
        self.name = name.strip()
        self.role = role.strip()
        self.scope = scope  # e.g., Portfolio, LargeSolution, or ARTx TeamSlug
        self.team_name = team_name
        self.art_label = art_label
        self.details: Dict[str, str] = {}  # Skills, Responsibilities, Relationships, Team, Data dependencies

    def file_dir(self) -> Path:
        base = ROOT / "agile-team"
        if self.scope.startswith("ART") and self.team_name:
            # Team-based directory: ARTn_<TeamSlug>
            dir_name = f"{self.scope}_{slugify(self.team_name)}"
        else:
            dir_name = slugify(self.scope)
        return base / dir_name

    def file_path(self) -> Path:
        filename = f"{slugify(self.name)}_{slugify(self.role.replace(' ', '_'))}.md"
        return self.file_dir() / filename

    def title_context(self) -> str:
        if self.team_name and self.scope.startswith("ART"):
            return f"{self.role} | {self.team_name} ({self.scope})"
        return f"{self.role} | {self.scope}"

    def render(self) -> str:
        skills = self.details.get("Skills", "")
        responsibilities = self.details.get("Responsibilities", "")
        relationships = self.details.get("Relationships", "")
        team = self.details.get("Team", "")
        data_deps = self.details.get("Data dependencies", "")

        # Build SMART and INVEST with role-aware placeholders
        smart = f"""
### SMART mission
- Specific: Execute {self.role.lower()} responsibilities for {self.team_name or self.scope}, ensuring alignment to architecture, roadmap, and ceremonies.
- Measurable: Deliver agreed outcomes per sprint/PI; meet KPIs defined below; complete integration points on schedule.
- Achievable: Leverage team capabilities ({team or 'cross-functional team'}) and skills ({skills or 'role-relevant expertise'}), escalating blockers early.
- Relevant: Directly supports program goals in {self.art_label or self.scope}, enabling value flow and system quality.
- Time-bound: Commit to sprint goals (2-week cadence) and PI objectives; report progress daily and at reviews.
""".strip()

        invest = f"""
### INVEST user story
As {self.name} ({self.role}), I will plan and deliver my responsibilities so that {self.team_name or self.scope} achieves its sprint and PI objectives.
- Independent: Work items are coordinated but not blocked by unrelated scope; define clear dependencies early.
- Negotiable: Collaborate with stakeholders ({relationships or 'stakeholders'}) to refine scope and acceptance criteria.
- Valuable: Outcomes increase capability, quality, or flow for {self.team_name or self.scope}.
- Estimable: Break down work into small, estimable tasks with DoD and acceptance tests.
- Small: Scope tasks to fit within a sprint to maximize feedback cycles.
- Testable: Define objective acceptance criteria and KPIs.
""".strip()

        kpis = """
### KPIs
- Delivery predictability (stories completed vs. committed)
- Quality (defect escape rate, rework)
- Flow (cycle time, WIP)
- Integration success (passed integration tests, resolved dependencies)
- Stakeholder satisfaction (demo feedback)
""".strip()

        inputs_outputs = f"""
### Inputs and outputs
- Inputs: Backlog items, architectural guidance, {('data dependencies: ' + data_deps) if data_deps else 'integration constraints'}, team capacity, Definition of Ready.
- Outputs: Completed increments meeting Definition of Done, documentation updates, integration artifacts (APIs, interfaces, test evidence).
""".strip()

        collab = f"""
### Collaboration and dependencies
- Relationships: {relationships or 'Coordinate with peers, architects, product, and RTEs'}
- Cross-team integration: Follow Critical Integration Points; align with architects and integration teams.
{('- Data dependencies: ' + data_deps) if data_deps else ''}
""".strip()

        cadence = """
### Operating cadence
- Daily standup, sprint planning/review/retro
- Scrum of Scrums / ART sync as applicable
- PI planning and system demos
""".strip()

        dod = """
### Definition of Done
- Meets acceptance criteria and passes tests (unit/integration/system as applicable)
- Integrated and verified at appropriate system level
- Documentation and evidence updated (including compliance where relevant)
""".strip()

        acceptance = f"""
### Acceptance criteria
- Responsibilities delivered: {responsibilities or 'Role-specific outcomes completed'}
- No critical defects; KPIs within agreed thresholds
- Integration points satisfied; stakeholders sign-off at review/demo
""".strip()

        header = f"# {self.name} — {self.title_context()}\n"
        context = f"""
## Role context
- Skills: {skills or 'N/A'}
- Responsibilities: {responsibilities or 'N/A'}
- Team: {team or (self.team_name or 'N/A')}
""".strip()

        sections = [header, context, smart, invest, inputs_outputs, kpis, collab, cadence, dod, acceptance]
        return "\n\n".join(sections).rstrip() + "\n"


def parse_document(text: str) -> List[Agent]:
    agents: List[Agent] = []
    current_scope = None  # Portfolio, LargeSolution, or ARTn
    current_team_name: Optional[str] = None
    current_art_label: Optional[str] = None
    current_agent: Optional[Agent] = None
    current_team_data_deps: Optional[str] = None

    # Patterns
    re_portfolio = re.compile(r"^## \*\*Portfolio Level.*")
    re_large = re.compile(r"^## \*\*Large Solution Level.*")
    re_art = re.compile(r"^### \*\*ART\s+(\d+):\s+(.+?)\*\*")
    re_team = re.compile(r"^#### \*\*Team\s+[^:]+:\s+(.+?)\*\*")
    re_agent = re.compile(r"^\*\*(.+?)\*\*\s+-\s+\*(.+?)\*")
    re_detail = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.*)")

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if re_portfolio.match(line):
            current_scope = "Portfolio"
            current_art_label = None
            current_team_name = None
            current_agent = None
            continue
        m_large = re_large.match(line)
        if m_large:
            current_scope = "LargeSolution"
            current_art_label = None
            current_team_name = None
            current_agent = None
            continue
        m_art = re_art.match(line)
        if m_art:
            art_num, art_name = m_art.groups()
            current_scope = f"ART{art_num}"
            current_art_label = f"ART {art_num}: {art_name}"
            current_team_name = None
            current_agent = None
            continue
        m_team = re_team.match(line)
        if m_team:
            current_team_name = m_team.group(1)
            current_agent = None
            current_team_data_deps = None
            continue
        m_agent = re_agent.match(line)
        if m_agent:
            name, role = m_agent.groups()
            scope_label = current_scope or "Unknown"
            agent = Agent(name=name, role=role, scope=scope_label, team_name=current_team_name, art_label=current_art_label)
            if current_team_data_deps:
                agent.details["Data dependencies"] = current_team_data_deps
            agents.append(agent)
            current_agent = agent
            continue
        m_detail = re_detail.match(line)
        if m_detail:
            key, val = m_detail.groups()
            key = key.strip()
            val = val.strip()
            if current_agent is not None:
                current_agent.details[key] = val
            else:
                # Capture team-level data dependencies (applies to all agents in team)
                if key == "Data dependencies" and current_team_name is not None:
                    current_team_data_deps = val

    return agents


def main() -> None:
    if not DOC.exists():
        raise SystemExit(f"Document not found: {DOC}")
    text = DOC.read_text(encoding="utf-8")
    agents = parse_document(text)
    if not agents:
        raise SystemExit("No agents parsed from document. Check formatting.")

    created = 0
    for agent in agents:
        out_dir = agent.file_dir()
        ensure_dir(out_dir)
        out_path = agent.file_path()
        content = agent.render()
        out_path.write_text(content, encoding="utf-8")
        created += 1

    print(f"Generated {created} prompt files in agile-team/*/*_*.md")


if __name__ == "__main__":
    main()
