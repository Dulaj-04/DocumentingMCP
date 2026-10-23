"""Plan-first workflow: requirements checklist, open questions, a rough plan the student approves,
then step-by-step execution with a check-in after every step."""

from __future__ import annotations

import datetime as dt
import json
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .profile import config_dir

# Defaults the student is asked to confirm or change before anything is written.
DEFAULT_SETTINGS = {
    "template": "assignment",
    "page_numbers": "bottom-center",
    "border_width_pt": 0.5,
    "border_style": "single",
    "table_style": "grid",
    "number_equations": False,
    "figure_captions": False,
    "toc": False,
    "export_pdf": True,
}

SETTING_HELP = {
    "template": "Document type: assignment (Q&A), lab_report or ca_report",
    "page_numbers": "Page numbers: bottom-center, bottom-right or none (cover never numbered)",
    "border_width_pt": "Page border thickness in pt: 0 (none), 0.25, 0.5, 0.75, 1, 1.5, 2.25, 3, 4.5 or 6",
    "border_style": "Page border style: single, double, thick-thin, dotted or dashed",
    "table_style": "Tables: grid (plain Word) or shaded (coloured header)",
    "number_equations": "Number every equation (1), (2), ...",
    "figure_captions": "Caption every figure (Figure n: ...)",
    "toc": "Table of contents after the cover",
    "export_pdf": "Also save a PDF at the end",
}

# Content requirements shown as a tick list. (key, label, default)
REQUIREMENTS = [
    ("answer_all_questions", "Answer every question / section the brief asks for", True),
    ("follow_brief_order", "Keep the brief's question order and numbering", True),
    ("use_lecture_notes", "Base the theory on the lecture notes / textbook provided", True),
    ("diagrams_where_asked", "Draw diagrams wherever a question says 'diagram', 'sketch' or 'draw'", True),
    ("plots_from_data", "Plot graphs from my readings / simulation data", False),
    ("worked_calculations", "Show full step-by-step working for numerical questions", True),
    ("equations_in_word_format", "Write all formulae as editable Word equations", True),
    ("ieee_references", "Cite sources with IEEE references [1], [2] ...", True),
    ("include_code", "Include program code (labs)", False),
    ("include_photos_screenshots", "Include my photos / screenshots", False),
    ("student_voice", "Write in a plain undergraduate voice (no AI-sounding wording)", True),
    ("similarity_check", "Run a similarity check against the notes before finishing", True),
    ("pre_submission_check", "Run the pre-submission check (spelling, units, limits)", True),
]

BASE_QUESTIONS = [
    ("module", "Module code and name (e.g. ET2013 – Analog Electronics)?"),
    ("title", "Title of the assignment or lab, as it should appear on the cover?"),
    ("submission_date", "Submission date (DD/MM/YYYY)?"),
    ("brief", "Do you have the assignment brief or lab sheet? Give its file path."),
    ("notes", "Which lecture notes, textbook chapters or papers should it be based on (file paths)?"),
    ("materials", "Any readings, data files, screenshots, photos or code to include (folder path)?"),
    ("limits", "Is there a word or page limit?"),
    ("lecturer_requirements", "Anything specific the lecturer asked for (format, sections, number of references, group details)?"),
]


@dataclass
class Plan:
    id: str
    request: str
    created: str
    status: str = "gathering_requirements"  # -> awaiting_approval -> approved -> in_progress -> done
    template: str = "assignment"
    requirements: dict = field(default_factory=dict)
    settings: dict = field(default_factory=lambda: dict(DEFAULT_SETTINGS))
    answers: dict = field(default_factory=dict)
    open_questions: list = field(default_factory=list)
    steps: list = field(default_factory=list)  # [{"n", "title", "status", "note"}]
    docx_path: str = ""
    history: list = field(default_factory=list)


def _dir() -> Path:
    d = config_dir() / "plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_plan(request: str, template: str = "") -> Plan:
    pid = dt.date.today().strftime("%Y%m%d") + "-" + secrets.token_hex(3)
    p = Plan(id=pid, request=request.strip(), created=dt.datetime.now().isoformat(timespec="seconds"))
    if template:
        p.template = template
        p.settings["template"] = template
    p.requirements = {k: d for k, _, d in REQUIREMENTS}
    p.open_questions = [{"key": k, "question": q} for k, q in BASE_QUESTIONS]
    save(p)
    return p


def save(p: Plan) -> None:
    (_dir() / f"{p.id}.json").write_text(json.dumps(asdict(p), indent=2, ensure_ascii=False), encoding="utf-8")


def load(plan_id: str) -> Plan:
    f = _dir() / f"{plan_id}.json"
    if not f.is_file():
        raise FileNotFoundError(f"No plan with id {plan_id}. Start one with start_assignment.")
    data = json.loads(f.read_text(encoding="utf-8"))
    return Plan(**{k: v for k, v in data.items() if k in Plan.__dataclass_fields__})


def checklist_markdown(p: Plan) -> str:
    lines = ["**Requirements (tick what you need):**"]
    labels = {k: lbl for k, lbl, _ in REQUIREMENTS}
    for k, val in p.requirements.items():
        lines.append(f"- [{'x' if val else ' '}] {labels.get(k, k)}")
    lines += ["", "**Defaults (say if you want any changed):**"]
    for k, val in p.settings.items():
        shown = {True: "yes", False: "no"}.get(val, val) if isinstance(val, bool) else val
        lines.append(f"- {SETTING_HELP.get(k, k)}: **{shown}**")
    return "\n".join(lines)


def plan_markdown(p: Plan) -> str:
    out = [f"### Plan {p.id}: {p.answers.get('title') or p.request[:60]}", "", checklist_markdown(p), "", "**Steps:**"]
    for s in p.steps:
        mark = {"done": "✔", "in_progress": "…", "needs_changes": "✎"}.get(s["status"], " ")
        out.append(f"{s['n']}. [{mark}] {s['title']}" + (f" ({s['note']})" if s.get("note") else ""))
    return "\n".join(out)
