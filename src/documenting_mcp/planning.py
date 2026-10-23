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
    ("my_input_sections", "Ask for my own input (results, problems, conclusions) before writing the sections I tick", True),
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
    ("group", "Is this a group assignment? If so, list each member's name and reg no."),
    ("lecturer_requirements", "Anything specific the lecturer asked for (format, sections, number of references, department on the cover)?"),
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
    sections: list = field(default_factory=list)  # [{"title", "my_input", "questions", "input"}]
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


# --------------------------------------------------------------------------- "get my input here"

import re as _re

# (keywords, suggest ticking?, questions to ask the student)
SECTION_QUESTIONS = [
    (("result", "observation", "measurement", "reading"), True, [
        "What did you actually see or measure? Give the real numbers / readings.",
        "Did anything not work the first time? What happened?",
        "Which of your screenshots or photos shows this?",
    ]),
    (("discussion", "analysis", "evaluation"), True, [
        "Why do you think the results came out the way they did?",
        "What problems did you hit, and how did you solve them?",
        "How do your results compare with the theory or expected values?",
        "What would you do differently next time?",
    ]),
    (("conclusion", "summary"), True, [
        "In one or two sentences, what did you learn?",
        "Was the aim achieved? Why or why not?",
    ]),
    (("procedure", "method", "methodology", "experimental"), True, [
        "Which steps did you actually follow (anything different from the lab sheet)?",
        "Which equipment, settings or software versions did you use?",
    ]),
    (("code", "program", "firmware", "implementation"), True, [
        "In your own words, what does your code do?",
        "Which part did you write or change yourself, and was anything tricky to debug?",
    ]),
    (("contribution", "individual"), True, [
        "What exactly did each member do?",
    ]),
    (("aim", "objective", "introduction"), False, [
        "In your own words, what was this work trying to show or achieve?",
    ]),
    (("theory", "background", "principle", "literature", "review"), False, [
        "Which lecture, notes or textbook section is this based on?",
        "Is there anything the lecturer emphasised that must be included?",
    ]),
    (("calculate", "find", "determine", "compute", "design", "numerical", "example"), True, [
        "Which values are you using? Have you worked it out yourself, and what answer did you get?",
        "Is there a method the lecturer expects (e.g. a particular formula or table)?",
    ]),
]
DEFAULT_QUESTIONS = [
    "What do you already understand about this question, in your own words?",
    "Any example from the lab, lectures or your own experience that should be included?",
    "Anything the lecturer stressed about this topic?",
]


def _norm_title(t: str) -> str:
    t = _re.sub(r"^\s*(?:Q(?:uestion)?\s*)?\d+(?:\.\d+)*\s*[.):]?\s*", "", t, flags=_re.I)
    return _re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def section_profile(title: str) -> tuple[bool, list[str]]:
    words = _norm_title(title)
    for keys, tick, questions in SECTION_QUESTIONS:
        if any(_re.search(rf"\b{k}", words) for k in keys):
            return tick, questions
    return False, DEFAULT_QUESTIONS


def find_section(p: Plan, title: str) -> dict | None:
    want = _norm_title(title)
    for s_ in p.sections:
        if _norm_title(s_["title"]) == want:
            return s_
    for s_ in p.sections:
        if want and (want in _norm_title(s_["title"]) or _norm_title(s_["title"]) in want):
            return s_
    return None


def missing_input(p: Plan, headings: list[str]) -> list[str]:
    """Ticked sections that appear in the body but have no student input yet."""
    if not p.requirements.get("my_input_sections", True):
        return []
    out = []
    for h in headings:
        s_ = find_section(p, h)
        if s_ and s_["my_input"] and not s_.get("input"):
            out.append(s_["title"])
    return out


def plan_markdown(p: Plan) -> str:
    out = [f"### Plan {p.id}: {p.answers.get('title') or p.request[:60]}", "", checklist_markdown(p)]
    if p.sections:
        out += ["", "**Sections: tick 'get my input here' where you want to give your own results/ideas:**"]
        for s_ in p.sections:
            got = " (input received)" if s_.get("input") else ""
            out.append(f"- [{'x' if s_['my_input'] else ' '}] {s_['title']}{got}")
    out += ["", "**Steps:**"]
    for s in p.steps:
        mark = {"done": "✔", "in_progress": "…", "needs_changes": "✎"}.get(s["status"], " ")
        out.append(f"{s['n']}. [{mark}] {s['title']}" + (f" ({s['note']})" if s.get("note") else ""))
    return "\n".join(out)
