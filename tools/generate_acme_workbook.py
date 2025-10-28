#!/usr/bin/env python3
import os
import re
import sys
import random
from datetime import date, timedelta
from typing import List, Dict, Optional
import argparse
import csv

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(ROOT, "save6", "SAFe6OrganizationStructure.md")
OUT_XLSX = os.path.join(ROOT, "ACME_Project_Team_Workload.xlsx")

random.seed(42)

# === Configurable planning parameters ===
# Total number of sprints to plan
SPRINT_COUNT = 8
# Calendar length of a sprint in days (e.g., 14 for a two-week sprint)
SPRINT_CALENDAR_LENGTH_DAYS = 14
# Working days used for capacity per sprint (e.g., 10 weekdays in a 2-week sprint)
WORKING_DAYS_PER_SPRINT = 10
# Hours per work day used for capacity calculation
HOURS_PER_WORK_DAY = 6.5
# Default capacity hours per sprint for each resource
DEFAULT_CAPACITY_HOURS_PER_SPRINT = WORKING_DAYS_PER_SPRINT * HOURS_PER_WORK_DAY

# Simple name pools per "universe" to assign themed names
MARVEL = [
    "Peter Parker","Steve Rogers","Tony Stark","Bruce Banner","Wanda Maximoff","Stephen Strange",
    "Scott Lang","T'Challa","Sam Wilson","Bucky Barnes","Carol Danvers","Clint Barton",
    "Gamora","Drax","Groot","Nebula","Mantis","Okoye","Shuri","Pepper Potts",
    "Johnny Storm","Ben Grimm","Kate Bishop","Monica Rambeau","Kamala Khan","Jennifer Walters",
    "Shang-Chi","Dane Whitman","Yelena Belova","Maria Hill","Phil Coulson","Jessica Jones",
    "Luke Cage","Matt Murdock","Danny Rand","Frank Castle","Quake Johnson","Hank Pym"
]
DC = [
    "John Stewart","Oliver Queen","Dinah Lance","Billy Batson","Zatanna Zatara","Tim Drake",
    "Jason Todd","Barbara Gordon","Cassandra Cain","Stephanie Brown","Roy Harper","Wally West",
    "Donna Troy","Kara Zor-El","Kaldur'ahm","Victor Zsasz","Rene Ramirez","Helena Bertinelli",
    "Rory Regan","Ryan Choi","Ted Kord","Jaime Reyes","Mari McCabe","Carter Hall","Kendra Saunders",
    "Eobard Thawne","Mera Nereus","Ravager Wilson","Talia al Ghul","Huntress Wayne"
]
BOND = [
    "James Bond","Felix Leiter","Alec Trevelyan","Vesper Lynd","Severine Moreau","Gareth Mallory",
    "Bill Tanner","Le Chiffre","Raoul Silva","Eve Moneypenny (Alt)","Q (Alt)","Camille Montes"
]
OLYMPIANS = [
    "Hera","Apollo","Artemis","Ares","Hephaestus","Demeter","Poseidon","Hestia","Dionysus"
]

UNIVERSE_POOLS = {
    "avengers": MARVEL,
    "guardians": MARVEL,
    "x-men": MARVEL,
    "fantastic four": MARVEL,
    "s.h.i.e.l.d": MARVEL,
    "justice league": DC,
    "teen titans": DC,
    "watchmen": DC,
    "olympus": OLYMPIANS,
    "portfolio": OLYMPIANS,
    "bond": BOND,
    "james bond": BOND,
}

used_names = set()

def pool_for_unit(unit: str) -> List[str]:
    u = (unit or "").lower()
    for key, pool in UNIVERSE_POOLS.items():
        if key in u:
            return pool
    # Fallback by ART keywords
    if any(k in u for k in ["art", "agile release train", "team"]):
        return MARVEL + DC
    return MARVEL + DC + BOND + OLYMPIANS


def themed_random_name(unit: str) -> str:
    pool = pool_for_unit(unit)
    # Try to find an unused name
    random.shuffle(pool)
    for name in pool:
        if name not in used_names:
            used_names.add(name)
            return name
    # If exhausted, synthesize a name with an index
    idx = len(used_names) + 1
    synth = f"{unit.title()} Member {idx}"
    used_names.add(synth)
    return synth


class Resource:
    def __init__(self, name: str, role: str, level: str, art: Optional[str], art_name: Optional[str], team: Optional[str], unit: Optional[str]):
        self.name = name
        self.role = role
        self.level = level
        self.art = art
        self.art_name = art_name
        self.team = team
        self.unit = unit

    def as_row(self):
        return [self.name, self.role, self.level, self.art or "", self.team or "", self.unit or ""]


def parse_org_markdown(md_text: str) -> Dict[str, List[Resource]]:
    resources: List[Resource] = []
    stakeholders: List[Resource] = []

    level = None  # Portfolio, Large Solution, ART
    current_art = None
    current_art_name = None
    current_team = None
    current_team_display = None
    team_specialties: Dict[str, List[str]] = {}

    # Regex for person-role lines like **Batman** - *Product Manager*
    person_role_re = re.compile(r"^\*\*(.+?)\*\*\s*-\s*\*(.+?)\*")
    art_header_re = re.compile(r"^###\s*\*\*(ART\s*\d+):\s*(.+?)\*\*")
    team_header_re = re.compile(r"^####\s*\*\*(Team\s*(Alpha|Beta)):\s*(.+?)\*\*")

    lines = md_text.splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## **Portfolio Level"):
            level = "Portfolio"
            current_art = None
            current_team = None
            continue
        if line.startswith("## **Large Solution Level"):
            level = "Large Solution"
            current_art = None
            current_team = None
            continue
        m_art = art_header_re.match(line)
        if m_art:
            level = "ART"
            current_art = m_art.group(1)
            current_art_name = m_art.group(2)
            current_team = None
            continue
        m_team = team_header_re.match(line)
        if m_team:
            current_team = m_team.group(1)
            current_team_display = m_team.group(3)
            # initialize specialties store
            team_specialties.setdefault(current_team_display, [])
            continue
        # Capture specialties lines: - **Team**: ...
        if line.startswith("- **Team**:"):
            # e.g., "- **Team**: UI/UX developers, Mission Planning specialists"
            payload = line.split(":", 1)[1].strip()
            parts = [p.strip() for p in payload.split(",") if p.strip()]
            # normalize role names to singular/title case
            norm = []
            for p in parts:
                p = re.sub(r"\s+developers?", " Developer", p, flags=re.I)
                p = re.sub(r"\s+engineers?", " Engineer", p, flags=re.I)
                p = re.sub(r"\s+specialists?", " Specialist", p, flags=re.I)
                p = re.sub(r"\s+systems?", " System", p, flags=re.I)
                p = re.sub(r"\s+analysis", " Analyst", p, flags=re.I)
                norm.append(p.title())
            if current_team_display:
                team_specialties[current_team_display].extend(norm)
            continue

        # Person/Role lines
        m_pr = person_role_re.match(line)
        if m_pr:
            person = m_pr.group(1).strip()
            role = m_pr.group(2).strip()
            unit_hint = current_team_display or current_art_name or level
            # Record the resource
            res = Resource(person, role, level or "", current_art, current_art_name, current_team, unit_hint)
            resources.append(res)
            # Consider most leadership roles as stakeholders
            if role.lower() in {"portfolio epic owner","portfolio architect","portfolio coordinator","solution train engineer","solution architect","solution management","product manager","release train engineer","system architect","scrum master"}:
                stakeholders.append(res)
            continue

    # Generate additional team members based on specialties
    for team_name, roles in team_specialties.items():
        # Determine ART and level for the team by scanning resources already tied to this team_name
        team_context = next((r for r in resources if r.unit == team_name), None)
        level_ctx = team_context.level if team_context else "ART"
        art_ctx = team_context.art if team_context else None
        art_name_ctx = team_context.art_name if team_context else None
        team_label = team_context.team if team_context else None
        for role in roles:
            # Create 2 members for each specialty role
            for _ in range(2):
                name = themed_random_name(team_name)
                resources.append(Resource(name, role, level_ctx, art_ctx, art_name_ctx, team_label, team_name))

    return {"resources": resources, "stakeholders": stakeholders}


def next_monday(from_date: date) -> date:
    days_ahead = (0 - from_date.weekday() + 7) % 7  # Monday=0
    if days_ahead == 0:
        days_ahead = 7
    return from_date + timedelta(days=days_ahead)


def style_header(ws, row=1):
    bold = Font(bold=True)
    fill = PatternFill("solid", fgColor="FFE599")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for cell in ws[row]:
        cell.font = bold
        cell.fill = fill
        cell.alignment = center
        cell.border = border


def set_col_widths(ws, widths: Dict[int, float]):
    for col_idx, width in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width


def build_workbook(data: Dict[str, List[Resource]]):
    wb = Workbook()
    # Remove default sheet
    default = wb.active
    wb.remove(default)

    resources: List[Resource] = data["resources"]
    stakeholders: List[Resource] = data["stakeholders"]

    # Project Info
    ws = wb.create_sheet("Project_Info")
    ws.append(["Field", "Value"]) 
    ws.append(["Project Name", "ACME Systems Engineering - Drone Swarm System (Example)"])
    ws.append(["Description", "Workbook for team organization, stakeholders, and resource workload tracking."])
    ws.append(["Owner", "Moneypenny (Solution Management)"])
    ws.append(["Version", "1.0"])
    ws.append(["Last Generated", date.today().isoformat()])
    style_header(ws, 1)
    set_col_widths(ws, {1: 30, 2: 100})

    # Sprints
    ws_sprints = wb.create_sheet("Sprints")
    ws_sprints.append(["Sprint", "Start", "End", "Length (days)"])
    start = next_monday(date.today())
    for i in range(1, SPRINT_COUNT + 1):
        s = start + timedelta(days=(i-1)*SPRINT_CALENDAR_LENGTH_DAYS)
        e = s + timedelta(days=SPRINT_CALENDAR_LENGTH_DAYS-1)
        ws_sprints.append([f"Sprint {i}", s.isoformat(), e.isoformat(), SPRINT_CALENDAR_LENGTH_DAYS])
    style_header(ws_sprints, 1)
    set_col_widths(ws_sprints, {1: 12, 2: 14, 3: 14, 4: 14})

    # Stakeholders
    ws_st = wb.create_sheet("Stakeholders")
    ws_st.append(["Name","Role","Level","ART","Team","Unit","Influence","Interest","Engagement Plan","Contact"])
    for r in stakeholders:
        influence = "High" if r.level in ("Portfolio","Large Solution") or r.role.lower() in ("product manager","solution train engineer","solution architect") else "Medium"
        interest = "High" if r.role.lower() in ("product manager","release train engineer","system architect","scrum master") else "Medium"
        ws_st.append([r.name, r.role, r.level, r.art or "", r.team or "", r.unit or "", influence, interest, "", ""])
    style_header(ws_st, 1)
    set_col_widths(ws_st, {1: 22,2:22,3:14,4:10,5:14,6:24,7:12,8:12,9:30,10:24})

    # Organization
    ws_org = wb.create_sheet("Organization")
    ws_org.append(["Level","ART","ART Name","Team","Unit","Role","Name","Notes"])
    for r in resources:
        ws_org.append([r.level, r.art or "", r.art_name or "", r.team or "", r.unit or "", r.role, r.name, ""])
    style_header(ws_org, 1)
    set_col_widths(ws_org, {1:16,2:8,3:26,4:14,5:24,6:26,7:22,8:30})

    # Teams summary
    ws_tm = wb.create_sheet("Teams")
    ws_tm.append(["ART","Team","Unit","Role","Count"])
    # Simple aggregation: count roles per team
    from collections import defaultdict
    counts = defaultdict(int)
    units = {}
    for r in resources:
        key = (r.art or "", r.team or "", r.unit or "", r.role)
        counts[key] += 1
        units[(r.art or "", r.team or "")] = r.unit or ""
    for (art, team, unit, role), count in sorted(counts.items()):
        ws_tm.append([art, team, unit, role, count])
    style_header(ws_tm, 1)
    set_col_widths(ws_tm, {1:8,2:16,3:24,4:28,5:10})

    # Activities (Backlog) – provide a template and a few sample rows from cross-team dependencies
    ws_act = wb.create_sheet("Activities")
    ws_act.append(["ID","Title","Team","ART","Assigned To","Role","Sprint","Estimate (h)","Status","Priority","Dependency"]) 
    samples = [
        ("A-001","GCS-Airborne interface contract","Justice League Command","ART 1","Batman","Product Manager","Sprint 1",6,"Planned","High","Professor X"),
        ("A-002","Secure comms requirement baseline","Teen Titans Communication","ART 3","Raven","Product Manager","Sprint 2",8,"Planned","High","Nick Fury"),
        ("A-003","Swarm/Flight behavior API","X-Men Coordination","ART 6","Jean Grey","Product Manager","Sprint 2",10,"Planned","High","Professor X"),
        ("A-004","Integration test plan v1","Avengers Assembly","ART 7","Thor","Product Manager","Sprint 1",12,"Planned","High","ALL"),
    ]
    for row in samples:
        ws_act.append(list(row))
    style_header(ws_act, 1)
    set_col_widths(ws_act, {1:10,2:40,3:28,4:10,5:22,6:20,7:12,8:14,9:14,10:12,11:30})

    # RACI matrix – template
    ws_raci = wb.create_sheet("RACI")
    ws_raci.append(["Activity","Zeus","Athena","Hermes","M","Q","Moneypenny","Product Managers","RTEs","System Architects","Scrum Masters"]) 
    activities = [
        "PI Planning (Portfolio)",
        "Solution PI Planning",
        "Architecture Sync",
        "Monthly Stakeholder Review",
        "Solution Demo",
        "Security Review",
    ]
    raci_rows = {
        "PI Planning (Portfolio)": ["A","C","I","R","C","I","C","I","I","I"],
        "Solution PI Planning":     ["I","C","I","A","C","R","C","R","C","I"],
        "Architecture Sync":        ["I","A","I","C","R","I","I","I","R","I"],
        "Monthly Stakeholder Review":["A","C","R","I","I","R","C","I","I","I"],
        "Solution Demo":            ["I","I","I","A","C","R","R","R","C","C"],
        "Security Review":          ["I","C","I","C","C","I","C","I","R","I"],
    }
    for act in activities:
        ws_raci.append([act]+raci_rows.get(act, ["I"]*9))
    style_header(ws_raci, 1)
    set_col_widths(ws_raci, {1:36,2:10,3:10,4:10,5:10,6:10,7:14,8:18,9:10,10:16,11:16})

    # Risks & Issues – template
    ws_ri = wb.create_sheet("Risks_Issues")
    ws_ri.append(["ID","Type","Title","Description","Owner","Impact","Probability","Mitigation","Status","Target Sprint"])
    style_header(ws_ri, 1)
    set_col_widths(ws_ri, {1:10,2:10,3:30,4:60,5:22,6:10,7:12,8:40,9:12,10:14})

    # Resource Workload sheet
    ws_rw = wb.create_sheet("Resource_Workload")
    # Header
    base_headers = ["Resource","Role","Level","ART","Team","Unit","Cap Hrs/Sprint"]
    alloc_headers = [f"S{i} %" for i in range(1, SPRINT_COUNT + 1)]
    hours_headers = [f"S{i} Hrs" for i in range(1, SPRINT_COUNT + 1)]
    tail_headers = ["Total Hrs","Avg Util %","Over/Under Hrs"]
    ws_rw.append(base_headers + alloc_headers + hours_headers + tail_headers)
    style_header(ws_rw, 1)

    # Populate rows
    start_row = 2
    for idx, r in enumerate(resources, start=start_row):
        # Build the row with dynamic number of sprint columns
        row = [r.name, r.role, r.level, r.art or "", r.team or "", r.unit or "", DEFAULT_CAPACITY_HOURS_PER_SPRINT]
        row += [0] * SPRINT_COUNT  # allocations
        row += [0] * SPRINT_COUNT  # hours
        row += [0, 0, 0]           # totals
        ws_rw.append(row)
        # Index helpers
        cap_col = 7
        alloc_start_col = 8
        alloc_end_col = alloc_start_col + SPRINT_COUNT - 1
        hours_start_col = alloc_end_col + 1
        hours_end_col = hours_start_col + SPRINT_COUNT - 1
        total_col = hours_end_col + 1
        avg_col = total_col + 1
        over_col = avg_col + 1
        # Formulas for hours per sprint: hours = cap * percent
        for s in range(SPRINT_COUNT):
            alloc_col = alloc_start_col + s
            hrs_col = hours_start_col + s
            ws_rw.cell(row=idx, column=hrs_col).value = f"={get_column_letter(cap_col)}{idx}*{get_column_letter(alloc_col)}{idx}"
        # Total
        ws_rw.cell(row=idx, column=total_col).value = f"=SUM({get_column_letter(hours_start_col)}{idx}:{get_column_letter(hours_end_col)}{idx})"
        # Avg Util
        ws_rw.cell(row=idx, column=avg_col).value = f"=AVERAGE({get_column_letter(alloc_start_col)}{idx}:{get_column_letter(alloc_end_col)}{idx})"
        # Over/Under relative to sprint count
        ws_rw.cell(row=idx, column=over_col).value = f"={get_column_letter(total_col)}{idx}-{get_column_letter(cap_col)}{idx}*{SPRINT_COUNT}"

    # Widths
    widths = {1:22,2:22,3:14,4:8,5:16,6:28,7:14}
    for c in range(SPRINT_COUNT):
        widths[8+c] = 8
    for c in range(SPRINT_COUNT):
        widths[8+SPRINT_COUNT+c] = 10
    tail_start = 7 + 2*SPRINT_COUNT + 1
    widths[tail_start] = 12
    widths[tail_start+1] = 12
    widths[tail_start+2] = 14
    set_col_widths(ws_rw, widths)
    ws_rw.freeze_panes = "H2"  # freeze before allocations

    # Summary by ART (pivot-style via formulas)
    ws_art = wb.create_sheet("Summary_ART")
    # Headers
    art_headers = [
        "ART","Headcount","Total Cap/Sprint",
    ] + [f"S{i} Hrs" for i in range(1, SPRINT_COUNT + 1)] + [
        "Total Hrs","Overall Util %","Avg Util %","Over/Under Hrs"
    ]
    ws_art.append(art_headers)
    style_header(ws_art, 1)
    set_col_widths(ws_art, {1:10,2:12,3:16,4:10,5:10,6:10,7:10,8:10,9:10,10:10,11:10,12:12,13:16,14:12,15:16})

    # Distinct ARTs
    distinct_arts = sorted({(r.art or "").strip() for r in resources if (r.art or "").strip()})
    for i, art in enumerate(distinct_arts, start=2):
        ws_art.cell(row=i, column=1, value=art)
        a_ref = f"$A{i}"
        # Base counts and capacity (ART=D, CAP=G)
        ws_art.cell(row=i, column=2, value=f"=COUNTIF(Resource_Workload!$D:$D,{a_ref})")
        ws_art.cell(row=i, column=3, value=f"=SUMIF(Resource_Workload!$D:$D,{a_ref},Resource_Workload!$G:$G)")
        # Dynamic per-sprint hours from Resource_Workload
        alloc_start_col = 8
        hours_start_col = alloc_start_col + SPRINT_COUNT
        out_col = 4
        for s in range(SPRINT_COUNT):
            hrs_letter = get_column_letter(hours_start_col + s)
            ws_art.cell(row=i, column=out_col, value=f"=SUMIF(Resource_Workload!$D:$D,{a_ref},Resource_Workload!${hrs_letter}:${hrs_letter})")
            out_col += 1
        # Tail columns on Resource_Workload
        total_col_rw = hours_start_col + SPRINT_COUNT
        avg_col_rw = total_col_rw + 1
        over_col_rw = avg_col_rw + 1
        ws_art.cell(row=i, column=out_col, value=f"=SUMIF(Resource_Workload!$D:$D,{a_ref},Resource_Workload!${get_column_letter(total_col_rw)}:${get_column_letter(total_col_rw)})")
        out_col += 1
        ws_art.cell(row=i, column=out_col, value=f"=IFERROR({get_column_letter(out_col-1)}{i}/({get_column_letter(3)}{i}*{SPRINT_COUNT}),0)")
        out_col += 1
        ws_art.cell(row=i, column=out_col, value=f"=AVERAGEIF(Resource_Workload!$D:$D,{a_ref},Resource_Workload!${get_column_letter(avg_col_rw)}:${get_column_letter(avg_col_rw)})")
        out_col += 1
        ws_art.cell(row=i, column=out_col, value=f"=SUMIF(Resource_Workload!$D:$D,{a_ref},Resource_Workload!${get_column_letter(over_col_rw)}:${get_column_letter(over_col_rw)})")

    # Summary by Team (ART + Team + Unit)
    ws_team = wb.create_sheet("Summary_Team")
    team_headers = [
        "ART","Team","Unit","Headcount","Total Cap/Sprint",
    ] + [f"S{i} Hrs" for i in range(1, SPRINT_COUNT + 1)] + [
        "Total Hrs","Overall Util %","Avg Util %","Over/Under Hrs"
    ]
    ws_team.append(team_headers)
    style_header(ws_team, 1)
    set_col_widths(ws_team, {1:10,2:14,3:28,4:12,5:16,6:10,7:10,8:10,9:10,10:10,11:10,12:10,13:10,14:12,15:16,16:12,17:16})

    distinct_team_keys = sorted({(r.art or "", r.team or "", r.unit or "") for r in resources if (r.art or "").strip() and (r.team or "").strip()})
    for i, (art, team, unit) in enumerate(distinct_team_keys, start=2):
        ws_team.cell(row=i, column=1, value=art)
        ws_team.cell(row=i, column=2, value=team)
        ws_team.cell(row=i, column=3, value=unit)
        a_ref = f"$A{i}"  # ART
        b_ref = f"$B{i}"  # Team
        c_ref = f"$C{i}"  # Unit
        # COUNTIFS over ART(D), Team(E), Unit(F)
        ws_team.cell(row=i, column=4, value="=COUNTIFS(Resource_Workload!$D:$D,"+a_ref+",Resource_Workload!$E:$E,"+b_ref+",Resource_Workload!$F:$F,"+c_ref+")")
        ws_team.cell(row=i, column=5, value="=SUMIFS(Resource_Workload!$G:$G,Resource_Workload!$D:$D,"+a_ref+",Resource_Workload!$E:$E,"+b_ref+",Resource_Workload!$F:$F,"+c_ref+")")
        # Dynamic hours cols on Resource_Workload
        alloc_start_col = 8
        hours_start_col = alloc_start_col + SPRINT_COUNT
        out_col = 6
        for s in range(SPRINT_COUNT):
            hrs_letter = get_column_letter(hours_start_col + s)
            ws_team.cell(row=i, column=out_col, value=f"=SUMIFS(Resource_Workload!${hrs_letter}:${hrs_letter},Resource_Workload!$D:$D,{a_ref},Resource_Workload!$E:$E,{b_ref},Resource_Workload!$F:$F,{c_ref})")
            out_col += 1
        # Tail columns from RW
        total_col_rw = hours_start_col + SPRINT_COUNT
        avg_col_rw = total_col_rw + 1
        over_col_rw = avg_col_rw + 1
        ws_team.cell(row=i, column=out_col, value=f"=SUMIFS(Resource_Workload!${get_column_letter(total_col_rw)}:${get_column_letter(total_col_rw)},Resource_Workload!$D:$D,{a_ref},Resource_Workload!$E:$E,{b_ref},Resource_Workload!$F:$F,{c_ref})")
        out_col += 1
        ws_team.cell(row=i, column=out_col, value=f"=IFERROR({get_column_letter(out_col-1)}{i}/({get_column_letter(5)}{i}*{SPRINT_COUNT}),0)")
        out_col += 1
        ws_team.cell(row=i, column=out_col, value=f"=AVERAGEIFS(Resource_Workload!${get_column_letter(avg_col_rw)}:${get_column_letter(avg_col_rw)},Resource_Workload!$D:$D,{a_ref},Resource_Workload!$E:$E,{b_ref},Resource_Workload!$F:$F,{c_ref})")
        out_col += 1
        ws_team.cell(row=i, column=out_col, value=f"=SUMIFS(Resource_Workload!${get_column_letter(over_col_rw)}:${get_column_letter(over_col_rw)},Resource_Workload!$D:$D,{a_ref},Resource_Workload!$E:$E,{b_ref},Resource_Workload!$F:$F,{c_ref})")

    # Dashboard – lightweight KPIs
    ws_dash = wb.create_sheet("Dashboard")
    ws_dash.append(["Metric","Value"]) 
    ws_dash.append(["Total Resources", f"=COUNTA(Resource_Workload!A:A)-1"])
    # Determine the Avg Util % column letter dynamically
    alloc_start_col = 8
    hours_start_col = alloc_start_col + SPRINT_COUNT
    total_col_rw = hours_start_col + SPRINT_COUNT
    avg_col_rw = total_col_rw + 1
    avg_letter = get_column_letter(avg_col_rw)
    ws_dash.append(["Avg Utilization (all)", f"=AVERAGE(Resource_Workload!{avg_letter}:{avg_letter})"])
    # Note: embed comparison string carefully to avoid quote escaping issues
    ws_dash.append(["Overutilized Count (>1.0 avg)", f"=COUNTIF(Resource_Workload!{avg_letter}:{avg_letter},\">1\")"])
    style_header(ws_dash, 1)
    set_col_widths(ws_dash, {1:36,2:24})

    wb.save(OUT_XLSX)
    return OUT_XLSX


def parse_tasks_csv(csv_path: str) -> List[Dict[str, str]]:
    tasks: List[Dict[str, str]] = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)
    return tasks


def normalize_tasks(tasks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    norm: List[Dict[str, str]] = []
    for row in tasks:
        # Support multiple header variants
        idv = row.get('ID') or row.get('Id') or row.get('TaskID') or ''
        title = row.get('Title') or row.get('Summary') or ''
        assignee = row.get('Assignee') or row.get('Owner') or row.get('Assigned To') or ''
        team = row.get('Team') or ''
        art = row.get('ART') or row.get('Art') or ''
        sprint = row.get('Sprint') or row.get('Iteration') or row.get('Sprint Number') or ''
        hours = row.get('Hours') or row.get('Actual (h)') or row.get('ActualHrs') or row.get('Estimate (h)') or row.get('EstimateHrs') or '0'
        status = row.get('Status') or ''
        try:
            # Accept 'Sprint 3' or '3'
            s_val = str(sprint).strip()
            if s_val.lower().startswith('sprint'):
                s_idx = int(s_val.split()[-1])
            else:
                s_idx = int(float(s_val)) if s_val else 0
        except Exception:
            s_idx = 0
        try:
            hrs = float(hours) if str(hours).strip() else 0.0
        except Exception:
            hrs = 0.0
        if not assignee:
            continue
        norm.append({
            'ID': str(idv),
            'Title': title,
            'Assignee': assignee,
            'Team': team,
            'ART': art,
            'SprintIndex': s_idx,
            'Hours': hrs,
            'Status': status,
        })
    return norm


def build_tasks_and_rollup_sheets(wb: Workbook, resources: List[Resource], tasks_csv: Optional[str]):
    if not tasks_csv or not os.path.exists(tasks_csv):
        return  # no-op
    tasks_raw = parse_tasks_csv(tasks_csv)
    tasks = normalize_tasks(tasks_raw)

    # Actual_Tasks sheet
    ws_tasks = wb.create_sheet("Actual_Tasks")
    headers = ["ID","Title","Assignee","Sprint","Hours","Team","ART","Status"]
    ws_tasks.append(headers)
    for t in tasks:
        ws_tasks.append([
            t['ID'], t['Title'], t['Assignee'],
            f"Sprint {t['SprintIndex']}" if t['SprintIndex'] else "",
            t['Hours'], t['Team'], t['ART'], t['Status']
        ])
    style_header(ws_tasks, 1)
    set_col_widths(ws_tasks, {1:12,2:40,3:24,4:12,5:10,6:18,7:10,8:14})

    # Map assignee -> resource context (ART, Team, Unit)
    res_index: Dict[str, Resource] = {r.name: r for r in resources}

    # Rollup per assignee per sprint
    from collections import defaultdict
    roll: Dict[str, List[float]] = defaultdict(lambda: [0.0]*SPRINT_COUNT)
    for t in tasks:
        s_idx = t['SprintIndex']
        if isinstance(s_idx, int) and 1 <= s_idx <= SPRINT_COUNT:
            roll[t['Assignee']][s_idx-1] += float(t['Hours'])

    # Build Actuals_Rollup sheet
    ws_roll = wb.create_sheet("Actuals_Rollup")
    roll_headers = ["Resource","ART","Team","Unit"] + [f"S{i} Hrs" for i in range(1, SPRINT_COUNT+1)] + ["Total Hrs"]
    ws_roll.append(roll_headers)
    for assignee, per_sprint in sorted(roll.items()):
        ctx = res_index.get(assignee)
        art = ctx.art if ctx else ""
        team = ctx.team if ctx else ""
        unit = ctx.unit if ctx else ""
        total = sum(per_sprint)
        ws_roll.append([assignee, art or "", team or "", unit or ""] + per_sprint + [total])
    style_header(ws_roll, 1)
    widths = {1:24,2:10,3:14,4:28}
    for i in range(SPRINT_COUNT):
        widths[5+i] = 10
    widths[5+SPRINT_COUNT] = 12
    set_col_widths(ws_roll, widths)

    # Summary sheets for actuals
    # By ART
    ws_a_art = wb.create_sheet("Summary_Actuals_ART")
    art_headers = ["ART"] + [f"S{i} Hrs" for i in range(1, SPRINT_COUNT+1)] + ["Total Hrs"]
    ws_a_art.append(art_headers)
    style_header(ws_a_art, 1)
    # Distinct ARTs from rollup sheet
    arts = sorted({row[1] for row in ws_roll.iter_rows(min_row=2, values_only=True) if row[1]})
    for i, art in enumerate(arts, start=2):
        ws_a_art.cell(row=i, column=1, value=art)
        a_ref = f"$A{i}"
        # SUMIF over Actuals_Rollup ART column (B)
        for s in range(SPRINT_COUNT):
            col_letter = get_column_letter(4 + 1 + s)  # columns after Resource(A), ART(B), Team(C), Unit(D)
            ws_a_art.cell(row=i, column=2+s, value=f"=SUMIF(Actuals_Rollup!$B:$B,{a_ref},Actuals_Rollup!${col_letter}:${col_letter})")
        # Total Hrs column in Actuals_Rollup is at index 4 + SPRINT_COUNT + 1
        total_letter = get_column_letter(4 + SPRINT_COUNT + 1)
        ws_a_art.cell(row=i, column=2+SPRINT_COUNT, value=f"=SUMIF(Actuals_Rollup!$B:$B,{a_ref},Actuals_Rollup!${total_letter}:${total_letter})")

    # By Team (ART+Team+Unit)
    ws_a_team = wb.create_sheet("Summary_Actuals_Team")
    team_headers = ["ART","Team","Unit"] + [f"S{i} Hrs" for i in range(1, SPRINT_COUNT+1)] + ["Total Hrs"]
    ws_a_team.append(team_headers)
    style_header(ws_a_team, 1)
    # Distinct keys
    keys = sorted({(row[1], row[2], row[3]) for row in ws_roll.iter_rows(min_row=2, values_only=True) if row[1] or row[2]})
    for i, (art, team, unit) in enumerate(keys, start=2):
        ws_a_team.cell(row=i, column=1, value=art)
        ws_a_team.cell(row=i, column=2, value=team)
        ws_a_team.cell(row=i, column=3, value=unit)
        a_ref = f"$A{i}"; b_ref = f"$B{i}"; c_ref = f"$C{i}"
        for s in range(SPRINT_COUNT):
            col_letter = get_column_letter(4 + 1 + s)
            ws_a_team.cell(row=i, column=4+s, value=f"=SUMIFS(Actuals_Rollup!${col_letter}:${col_letter},Actuals_Rollup!$B:$B,{a_ref},Actuals_Rollup!$C:$C,{b_ref},Actuals_Rollup!$D:$D,{c_ref})")
        total_letter = get_column_letter(4 + SPRINT_COUNT + 1)
        ws_a_team.cell(row=i, column=4+SPRINT_COUNT, value=f"=SUMIFS(Actuals_Rollup!${total_letter}:${total_letter},Actuals_Rollup!$B:$B,{a_ref},Actuals_Rollup!$C:$C,{b_ref},Actuals_Rollup!$D:$D,{c_ref})")


def build_variance_art(wb: Workbook):
    # Requires Summary_ART and Summary_Actuals_ART to exist
    if "Summary_ART" not in wb.sheetnames or "Summary_Actuals_ART" not in wb.sheetnames:
        return None
    ws_plan = wb["Summary_ART"]
    ws_act = wb["Summary_Actuals_ART"]

    # Create/overwrite variance sheet
    if "Summary_Variance_ART" in wb.sheetnames:
        del wb["Summary_Variance_ART"]
    ws_var = wb.create_sheet("Summary_Variance_ART")

    # Gather ART list from planned summary
    arts = [row[0] for row in ws_plan.iter_rows(min_row=2, values_only=True) if row[0]]

    # Headers: ART, Var S1..Sn, Planned Total, Actual Total, Var Total, Var %
    headers = ["ART"] + [f"Var S{i} Hrs" for i in range(1, SPRINT_COUNT+1)] + [
        "Planned Total Hrs","Actual Total Hrs","Var Total Hrs","Var Total %"
    ]
    ws_var.append(headers)

    # Column indices on Summary_ART and Summary_Actuals_ART
    # Planned per-sprint hours start at col 4; total at 4+SPRINT_COUNT
    plan_s_start = 4
    plan_total_col = 4 + SPRINT_COUNT
    # Actual per-sprint hours start at col 2; total at 2+SPRINT_COUNT
    act_s_start = 2
    act_total_col = 2 + SPRINT_COUNT

    for i, art in enumerate(arts, start=2):
        ws_var.cell(row=i, column=1, value=art)
        a_ref = f"$A{i}"
        # Per sprint variance = Actual - Planned via SUMIF against respective sheets
        out_col = 2
        for s in range(SPRINT_COUNT):
            plan_col_letter = get_column_letter(plan_s_start + s)
            act_col_letter = get_column_letter(act_s_start + s)
            formula = (
                f"=SUMIF(Summary_Actuals_ART!$A:$A,{a_ref},Summary_Actuals_ART!${act_col_letter}:${act_col_letter})"
                f"-SUMIF(Summary_ART!$A:$A,{a_ref},Summary_ART!${plan_col_letter}:${plan_col_letter})"
            )
            ws_var.cell(row=i, column=out_col, value=formula)
            out_col += 1
        # Planned total
        ws_var.cell(row=i, column=out_col, value=f"=SUMIF(Summary_ART!$A:$A,{a_ref},Summary_ART!${get_column_letter(plan_total_col)}:${get_column_letter(plan_total_col)})")
        out_col += 1
        # Actual total
        ws_var.cell(row=i, column=out_col, value=f"=SUMIF(Summary_Actuals_ART!$A:$A,{a_ref},Summary_Actuals_ART!${get_column_letter(act_total_col)}:${get_column_letter(act_total_col)})")
        out_col += 1
        # Variance total (Actual - Planned)
        ws_var.cell(row=i, column=out_col, value=f"={get_column_letter(out_col-1)}{i}-{get_column_letter(out_col-2)}{i}")
        out_col += 1
        # Variance %
        ws_var.cell(row=i, column=out_col, value=f"=IFERROR({get_column_letter(out_col-1)}{i}/{get_column_letter(out_col-3)}{i},0)")

    style_header(ws_var, 1)
    # Set widths
    widths = {1:12}
    for c in range(SPRINT_COUNT):
        widths[2+c] = 12
    tail_start = 2 + SPRINT_COUNT
    widths[tail_start] = 16
    widths[tail_start+1] = 16
    widths[tail_start+2] = 14
    widths[tail_start+3] = 12
    set_col_widths(ws_var, widths)

    # Conditional formatting: red for overrun (>0), green for underrun (<0)
    if ws_var.max_row > 1:
        from_row = 2
        to_row = ws_var.max_row
        # Per-sprint variance columns
        start_col = 2
        end_col = 1 + SPRINT_COUNT
        rng = f"{get_column_letter(start_col)}{from_row}:{get_column_letter(end_col)}{to_row}"
        red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        ws_var.conditional_formatting.add(rng, CellIsRule(operator='greaterThan', formula=['0'], fill=red_fill))
        ws_var.conditional_formatting.add(rng, CellIsRule(operator='lessThan', formula=['0'], fill=green_fill))
        # Total variance column (Var Total Hrs)
        var_total_col = tail_start + 2
        rng_total = f"{get_column_letter(var_total_col)}{from_row}:{get_column_letter(var_total_col)}{to_row}"
        ws_var.conditional_formatting.add(rng_total, CellIsRule(operator='greaterThan', formula=['0'], fill=red_fill))
        ws_var.conditional_formatting.add(rng_total, CellIsRule(operator='lessThan', formula=['0'], fill=green_fill))
    return arts


def update_dashboard_with_art_chart(wb: Workbook, arts: Optional[List[str]]):
    if "Dashboard" not in wb.sheetnames or arts is None:
        return
    ws_dash = wb["Dashboard"]
    # Start a table after existing content
    start_row = ws_dash.max_row + 2
    ws_dash.cell(row=start_row, column=1, value="ART")
    ws_dash.cell(row=start_row, column=2, value="Planned Total Hrs")
    ws_dash.cell(row=start_row, column=3, value="Actual Total Hrs")
    ws_dash.cell(row=start_row, column=4, value="Variance Hrs")
    ws_dash.cell(row=start_row, column=5, value="Variance %")
    style_header(ws_dash, start_row)

    # Columns on Summary_Variance_ART
    # A: ART, then after SPRINT_COUNT variance columns we have Planned Total, Actual Total, Var, Var %
    var_ws = wb["Summary_Variance_ART"]
    for idx, art in enumerate(arts, start=start_row+1):
        # ART name
        ws_dash.cell(row=idx, column=1, value=art)
        a_ref = f"$A{idx}"
        # Fetch values via SUMIF from variance sheet
        # Compute column letters on variance sheet
        plan_total_col = 1 + 1 + SPRINT_COUNT  # A + VarCols + Planned Total
        act_total_col = plan_total_col + 1
        var_total_col = act_total_col + 1
        var_pct_col = var_total_col + 1
        ws_dash.cell(row=idx, column=2, value=f"=SUMIF(Summary_Variance_ART!$A:$A,{a_ref},Summary_Variance_ART!${get_column_letter(plan_total_col)}:${get_column_letter(plan_total_col)})")
        ws_dash.cell(row=idx, column=3, value=f"=SUMIF(Summary_Variance_ART!$A:$A,{a_ref},Summary_Variance_ART!${get_column_letter(act_total_col)}:${get_column_letter(act_total_col)})")
        ws_dash.cell(row=idx, column=4, value=f"=SUMIF(Summary_Variance_ART!$A:$A,{a_ref},Summary_Variance_ART!${get_column_letter(var_total_col)}:${get_column_letter(var_total_col)})")
        ws_dash.cell(row=idx, column=5, value=f"=SUMIF(Summary_Variance_ART!$A:$A,{a_ref},Summary_Variance_ART!${get_column_letter(var_pct_col)}:${get_column_letter(var_pct_col)})")

    # Create a clustered column chart comparing planned vs actual by ART
    data_start_row = start_row
    data_end_row = ws_dash.max_row
    if data_end_row > data_start_row:
        chart = BarChart()
        chart.type = "col"
        chart.title = "Planned vs Actual by ART"
        chart.y_axis.title = "Hours"
        chart.x_axis.title = "ART"
        # Series: columns 2 and 3, categories from column 1
        data_ref = Reference(ws_dash, min_col=2, min_row=data_start_row, max_col=3, max_row=data_end_row)
        cats_ref = Reference(ws_dash, min_col=1, min_row=data_start_row+1, max_row=data_end_row)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.height = 12
        chart.width = 24
        ws_dash.add_chart(chart, f"G2")


def build_variance_team(wb: Workbook):
    # Requires planned Summary_Team and actual Summary_Actuals_Team
    if "Summary_Team" not in wb.sheetnames or "Summary_Actuals_Team" not in wb.sheetnames:
        return None
    ws_plan = wb["Summary_Team"]
    ws_act = wb["Summary_Actuals_Team"]

    if "Summary_Variance_Team" in wb.sheetnames:
        del wb["Summary_Variance_Team"]
    ws_var = wb.create_sheet("Summary_Variance_Team")

    # Distinct (ART,Team,Unit) from planned sheet
    keys = [(row[0], row[1], row[2]) for row in ws_plan.iter_rows(min_row=2, values_only=True) if row[0] or row[1]]

    headers = ["ART","Team","Unit"] + [f"Var S{i} Hrs" for i in range(1, SPRINT_COUNT+1)] + [
        "Planned Total Hrs","Actual Total Hrs","Var Total Hrs","Var Total %"
    ]
    ws_var.append(headers)

    # Column indices on planned/actual team summaries
    # Planned per-sprint start at col 6; planned total at 6+SPRINT_COUNT
    plan_s_start = 6
    plan_total_col = 6 + SPRINT_COUNT
    # Actual per-sprint start at col 4; total at 4+SPRINT_COUNT
    act_s_start = 4
    act_total_col = 4 + SPRINT_COUNT

    for i, (art, team, unit) in enumerate(keys, start=2):
        ws_var.cell(row=i, column=1, value=art)
        ws_var.cell(row=i, column=2, value=team)
        ws_var.cell(row=i, column=3, value=unit)
        a_ref = f"$A{i}"; b_ref = f"$B{i}"; c_ref = f"$C{i}"
        out_col = 4
        for s in range(SPRINT_COUNT):
            plan_col_letter = get_column_letter(plan_s_start + s)
            act_col_letter = get_column_letter(act_s_start + s)
            formula = (
                f"=SUMIFS(Summary_Actuals_Team!${act_col_letter}:${act_col_letter},Summary_Actuals_Team!$A:$A,{a_ref},Summary_Actuals_Team!$B:$B,{b_ref},Summary_Actuals_Team!$C:$C,{c_ref})"
                f"-SUMIFS(Summary_Team!${plan_col_letter}:${plan_col_letter},Summary_Team!$A:$A,{a_ref},Summary_Team!$B:$B,{b_ref},Summary_Team!$C:$C,{c_ref})"
            )
            ws_var.cell(row=i, column=out_col, value=formula)
            out_col += 1
        # Planned total
        ws_var.cell(row=i, column=out_col, value=f"=SUMIFS(Summary_Team!${get_column_letter(plan_total_col)}:${get_column_letter(plan_total_col)},Summary_Team!$A:$A,{a_ref},Summary_Team!$B:$B,{b_ref},Summary_Team!$C:$C,{c_ref})")
        out_col += 1
        # Actual total
        ws_var.cell(row=i, column=out_col, value=f"=SUMIFS(Summary_Actuals_Team!${get_column_letter(act_total_col)}:${get_column_letter(act_total_col)},Summary_Actuals_Team!$A:$A,{a_ref},Summary_Actuals_Team!$B:$B,{b_ref},Summary_Actuals_Team!$C:$C,{c_ref})")
        out_col += 1
        # Variance total and %
        ws_var.cell(row=i, column=out_col, value=f"={get_column_letter(out_col-1)}{i}-{get_column_letter(out_col-2)}{i}")
        out_col += 1
        ws_var.cell(row=i, column=out_col, value=f"=IFERROR({get_column_letter(out_col-1)}{i}/{get_column_letter(out_col-3)}{i},0)")

    style_header(ws_var, 1)
    widths = {1:10,2:14,3:28}
    for c in range(SPRINT_COUNT):
        widths[4+c] = 12
    tail = 4 + SPRINT_COUNT
    widths[tail] = 16
    widths[tail+1] = 16
    widths[tail+2] = 14
    widths[tail+3] = 12
    set_col_widths(ws_var, widths)
    # Conditional formatting on team variance
    if ws_var.max_row > 1:
        from_row = 2
        to_row = ws_var.max_row
        # Per-sprint variance columns start at 4
        start_col = 4
        end_col = 3 + SPRINT_COUNT
        rng = f"{get_column_letter(start_col)}{from_row}:{get_column_letter(end_col)}{to_row}"
        red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        ws_var.conditional_formatting.add(rng, CellIsRule(operator='greaterThan', formula=['0'], fill=red_fill))
        ws_var.conditional_formatting.add(rng, CellIsRule(operator='lessThan', formula=['0'], fill=green_fill))
        # Var Total Hrs column at tail+2
        var_total_col = tail + 2
        rng_total = f"{get_column_letter(var_total_col)}{from_row}:{get_column_letter(var_total_col)}{to_row}"
        ws_var.conditional_formatting.add(rng_total, CellIsRule(operator='greaterThan', formula=['0'], fill=red_fill))
        ws_var.conditional_formatting.add(rng_total, CellIsRule(operator='lessThan', formula=['0'], fill=green_fill))
    return True


def build_stacked_chart_by_sprint_art(wb: Workbook):
    # Requires Summary_Actuals_ART
    if "Summary_Actuals_ART" not in wb.sheetnames:
        return None
    ws_src = wb["Summary_Actuals_ART"]
    # Create helper table sheet
    title = "Summary_Actuals_BySprint_ART"
    if title in wb.sheetnames:
        del wb[title]
    ws = wb.create_sheet(title)
    # Header: Sprint + ART names
    arts = [row[0] for row in ws_src.iter_rows(min_row=2, values_only=True) if row[0]]
    ws.cell(row=1, column=1, value="Sprint")
    for j, art in enumerate(arts, start=2):
        ws.cell(row=1, column=j, value=art)
    # Fill rows for S1..Sn and SUMIF values
    for i in range(1, SPRINT_COUNT+1):
        ws.cell(row=1+i, column=1, value=f"Sprint {i}")
        act_col_letter = get_column_letter(2 + (i-1))  # Summary_Actuals_ART per-sprint col
        for j in range(len(arts)):
            # criterion is header cell in this sheet (ART name)
            crit_ref = f"${get_column_letter(2+j)}$1"
            ws.cell(row=1+i, column=2+j, value=f"=SUMIF(Summary_Actuals_ART!$A:$A,{crit_ref},Summary_Actuals_ART!${act_col_letter}:${act_col_letter})")

    style_header(ws, 1)
    set_col_widths(ws, {1:12})
    for j in range(len(arts)):
        set_col_widths(ws, {2+j: 14})

    # Create stacked chart
    if len(arts) == 0:
        return None
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.title = "Actuals by ART per Sprint (stacked)"
    chart.y_axis.title = "Hours"
    chart.x_axis.title = "Sprint"
    data_ref = Reference(ws, min_col=2, min_row=1, max_col=1+len(arts), max_row=1+SPRINT_COUNT)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=1+SPRINT_COUNT)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.height = 14
    chart.width = 28
    # Place chart on the same sheet
    ws.add_chart(chart, "G2")
    return True


def main():
    global SPRINT_COUNT, SPRINT_CALENDAR_LENGTH_DAYS, WORKING_DAYS_PER_SPRINT, HOURS_PER_WORK_DAY, DEFAULT_CAPACITY_HOURS_PER_SPRINT, MD_PATH, OUT_XLSX

    parser = argparse.ArgumentParser(description="Generate ACME Project Team & Workload workbook from SAFe6 org markdown")
    parser.add_argument("--sprints", type=int, default=None, help="Number of sprints to plan (default: 8)")
    parser.add_argument("--length", type=int, default=None, help="Calendar length of a sprint in days (default: 14)")
    parser.add_argument("--working-days", type=int, default=None, help="Working days per sprint for capacity (default: 10)")
    parser.add_argument("--hours-per-day", type=float, default=None, help="Hours per work day for capacity (default: 6.5)")
    parser.add_argument("--capacity-hours", type=float, default=None, help="Override default capacity hours per sprint for each resource")
    parser.add_argument("--markdown", type=str, default=MD_PATH, help="Path to SAFe6OrganizationStructure.md")
    parser.add_argument("--out", type=str, default=OUT_XLSX, help="Output XLSX path")
    parser.add_argument("--tasks-csv", type=str, default=None, help="Path to CSV file of tasks to roll up actual hours per assignee")
    parser.add_argument("--stacked-chart", action="store_true", help="Add stacked chart by sprint across ARTs (requires --tasks-csv)")

    args = parser.parse_args()

    # Apply overrides to module-level config
    if args.sprints is not None and args.sprints > 0:
        SPRINT_COUNT = args.sprints
    if args.length is not None and args.length > 0:
        SPRINT_CALENDAR_LENGTH_DAYS = args.length
    if args.working_days is not None and args.working_days > 0:
        WORKING_DAYS_PER_SPRINT = args.working_days
    if args.hours_per_day is not None and args.hours_per_day > 0:
        HOURS_PER_WORK_DAY = args.hours_per_day
    # Recompute default capacity or override directly
    DEFAULT_CAPACITY_HOURS_PER_SPRINT = WORKING_DAYS_PER_SPRINT * HOURS_PER_WORK_DAY
    if args.capacity_hours is not None and args.capacity_hours > 0:
        DEFAULT_CAPACITY_HOURS_PER_SPRINT = args.capacity_hours

    if args.markdown:
        MD_PATH = args.markdown
    if args.out:
        OUT_XLSX = args.out

    if not os.path.exists(MD_PATH):
        print(f"Markdown not found: {MD_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()
    data = parse_org_markdown(md_text)
    # Build planned workbook first
    out = build_workbook(data)
    # Then optionally add actuals sheets if tasks CSV provided
    # Re-open the workbook to append actuals sheets in the same file
    from openpyxl import load_workbook
    wb = load_workbook(out)
    build_tasks_and_rollup_sheets(wb, data["resources"], args.tasks_csv)
    arts = build_variance_art(wb)
    build_variance_team(wb)
    if args.stacked_chart:
        build_stacked_chart_by_sprint_art(wb)
    update_dashboard_with_art_chart(wb, arts)
    wb.save(out)
    print(f"Workbook generated: {out}")


if __name__ == "__main__":
    main()
