"""MCP server: tools for generating KDU EE lab reports, CA reports and assignments as .docx/.pdf."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field, create_model
from mcp.server.transport_security import TransportSecuritySettings

from . import __version__, export, images as image_library, ingest, live_word, planning, project, quality, references
from .builder import BuildOptions, CoverInfo, build_report
from .guides import guide_for
from .profile import Profile, load_profile, save_profile
from .project import DocSource, load_source, save_source
from .styles import TEMPLATES

Template = Literal["lab_report", "ca_report", "assignment"]
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf"}

mcp = MCPServer(
    "KDocs MCP",
    version=__version__,
    instructions=(
        "Generates university engineering documents (lab reports, CA/simulation reports, Q&A assignments) "
        "as formatted Word files in the KDU EE house style. This is an INTERACTIVE, PLAN-FIRST workflow:\n"
        "1. get_profile (ask for missing name/reg no/intake, then set_profile).\n"
        "2. start_assignment as soon as the student describes a task. Do NOT write anything yet. Show the "
        "requirements checklist with tick boxes and the current defaults (page border, page numbers, tables, ...), "
        "and ask ALL open questions in one message. Wait for the reply.\n"
        "3. save_plan with their ticks, changed defaults, answers, the list of sections and a rough step-by-step "
        "plan; show the plan, including the 'get my input here' tick per section, and ask for approval or "
        "changes. approve_plan only after the student explicitly agrees.\n"
        "3b. Before writing any section ticked 'get my input here', call ask_section_input, ask the student, "
        "save their words with save_section_input, and build the section around what they said.\n"
        "4. Work through the plan one step at a time. After each step call update_plan_step, tell the student "
        "what was done, show the result, and ask whether to continue or change something. Never run the "
        "whole job silently.\n"
        "Tools along the way: extract_assignment_brief/read_source for briefs and notes, get_writing_guide, "
        "list_files, import_images/rename_image/list_images, ```plot/```diagram/```circuit blocks, spreadsheet_to_table, lookup_reference/add_reference, "
        "create_document(plan_id=...), review_figures + approve_figures (student approves every figure), "
        "update_section/replace_text for changes (applied live if the document is open in Word; open_in_word "
        "offers that; never pass overwrite_manual_edits=true without the student's consent), "
        "check_document and check_similarity before export_pdf."
    ),
)


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:60] or "document"


@mcp.tool()
def get_profile() -> dict:
    """Return the stored student details used on every cover page (name, reg no, intake, logo, output folder)."""
    p = load_profile()
    return {
        "name": p.name,
        "reg_no": p.reg_no,
        "intake": p.intake,
        "university": p.university,
        "department": p.department,
        "logo_path": str(p.logo()),
        "output_dir": str(p.out_dir()),
        "missing_fields": p.missing(),
    }


@mcp.tool()
def set_profile(
    name: str | None = None,
    reg_no: str | None = None,
    intake: str | None = None,
    university: str | None = None,
    department: str | None = None,
    logo_path: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """Save student details once so every document reuses them. Only the fields given are changed.

    name: as it should appear on the cover, e.g. "A B C Student".
    reg_no: e.g. "D/ENG/EE/25/0000".
    intake: e.g. "42".
    department: use a newline to control the line break on the cover.
    logo_path: optional custom crest image; the KDU crest is bundled by default.
    output_dir: folder where documents are saved (default: Documents/KDocs).
    """
    p = load_profile()
    for key, val in dict(
        name=name,
        reg_no=reg_no,
        intake=intake,
        university=university,
        department=department,
        logo_path=logo_path,
        output_dir=output_dir,
    ).items():
        if val is not None:
            setattr(p, key, val.strip())
    if logo_path and not Path(logo_path).expanduser().is_file():
        return {"error": f"Logo file not found: {logo_path}"}
    where = save_profile(p)
    return {"saved_to": str(where), **get_profile()}


@mcp.tool()
def list_templates() -> list[dict]:
    """List the available document templates and their usual section order."""
    return [{"template": t.key, "description": t.label, "sections": list(t.sections)} for t in TEMPLATES.values()]


@mcp.tool()
def get_writing_guide(template: Template) -> str:
    """Return the structure, writing style and Markdown conventions for a template. Read this before create_document."""
    return guide_for(template)


@mcp.tool()
def list_files(folder: str, images_only: bool = True) -> dict:
    """List files in a folder (e.g. the student's screenshots) so they can be referenced as images in the body."""
    root = Path(folder).expanduser()
    if not root.is_dir():
        return {"error": f"Not a folder: {folder}"}
    files = []
    for f in sorted(root.rglob("*")):
        if f.is_file() and (not images_only or f.suffix.lower() in IMAGE_EXT):
            files.append(str(f.relative_to(root)).replace("\\", "/"))
        if len(files) >= 500:
            break
    return {"folder": str(root), "files": files}


@mcp.tool()
def import_images(sources: list[str], names: list[str] | None = None, project: str = "") -> dict:
    """Collect the student's screenshots and photos in one folder (Downloads/KDocs Images) with tidy names.

    sources: image files and/or folders (every image inside a folder is taken). Originals are copied, never
        moved or deleted.
    names: optional new names, one per image in order (descriptive, e.g. "adc-block-diagram"). The extension
        is kept and a number is added if the name is taken. Look at each image first and name it by what it shows.
    project: optional sub-folder, e.g. "ET2013-lab3", to keep one assignment's images together.
    Afterwards refer to an image in the report by its file name only: `![caption](adc-block-diagram.png)`.
    """
    return image_library.import_images(sources, names, project)


@mcp.tool()
def list_images(project: str = "") -> dict:
    """List the images in the image library with their size and shape (landscape / portrait / square) so
    you can choose where each belongs and whether two or three should sit side by side."""
    return image_library.list_library(project)


@mcp.tool()
def rename_image(path: str, new_name: str, update_documents: list[str] | None = None) -> dict:
    """Rename an image inside the image library. The extension is kept.

    path: file name or library-relative path. Only files inside the library can be renamed.
    update_documents: .docx files that already use the image; their references are updated and they are
        rebuilt, so nothing breaks.
    """
    res = image_library.rename(path, new_name)
    if "error" in res or not res.get("renamed"):
        return res
    old_name, new_file = Path(res["old"]).name, Path(res["path"]).name
    updated = []
    for d in update_documents or []:
        try:
            src = load_source(d)
        except Exception as exc:
            updated.append({"docx": d, "error": str(exc)})
            continue
        pattern = re.compile(r"(?<![\w.-])((?:[^\s()]*[/\\])?)" + re.escape(old_name))
        body, n = pattern.subn(lambda m: m.group(1) + new_file, src.body_markdown)
        if n:
            src.body_markdown = body
            updated.append({"docx": d, "references": n, **_rebuild(d, src, False, f"Image renamed to {new_file}.")})
        else:
            updated.append({"docx": d, "references": 0})
    res["documents"] = updated
    return res


PageNumbers = Literal["none", "bottom-center", "bottom-right"]


def _references_for(src: DocSource) -> dict[str, dict]:
    refs = dict(references.load_library())
    for e in src.references:
        e = dict(e)
        key = e.pop("key", None) or references.make_key(e, set(refs))
        refs[key] = e
    return refs


def _build(src: DocSource, export_pdf: bool = False, out_path: Path | None = None) -> dict:
    opts = src.options
    style = TEMPLATES[src.template].with_overrides(
        figure_captions=opts.get("figure_captions") or None,
        number_equations=opts.get("number_equations") or None,
        scientific_math=opts.get("scientific_equations", True),
        title_font=opts.get("title_font") or None,
        table_style=opts.get("table_style") or None,
    )
    profile: Profile = load_profile()
    for key in ("name", "reg_no", "intake"):
        if getattr(src, key):
            setattr(profile, key, getattr(src, key))
    if out_path is None:
        stem = src.filename or f"{_slug(profile.reg_no.split('/')[-1]) + '_' if profile.reg_no else ''}{_slug(src.title)}"
        out_path = profile.out_dir() / f"{_slug(stem)}.docx"
    assets = Path(src.assets_dir).expanduser() if src.assets_dir else None
    build_opts = BuildOptions(
        references=_references_for(src),
        figures_dir=out_path.parent / f"{out_path.stem}_figures",
        toc=bool(opts.get("toc")),
        list_of_figures=bool(opts.get("list_of_figures")),
        list_of_tables=bool(opts.get("list_of_tables")),
        page_numbers=opts.get("page_numbers") or "bottom-center",
        header_text=opts.get("header_text") or "",
        footer_text=opts.get("footer_text") or "",
        approvals=dict(src.approvals),
        border_width_pt=float(opts.get("border_width_pt", 0.5)),
        border_style=opts.get("border_style") or "single",
        body_markdown=src.body_markdown,
    )
    result = build_report(
        style=style,
        profile=profile,
        cover=CoverInfo(
            title=src.title.strip(), module=src.module.strip(), submission_date=src.submission_date,
            department=opts.get("department") or "", members=list(opts.get("members") or []),
        ),
        markdown=src.body_markdown,
        out_path=out_path,
        assets_dir=assets,
        options=build_opts,
    )
    src.built_hash = project.file_hash(result.path)
    save_source(result.path, src)
    response: dict = {"docx": str(result.path), "warnings": result.warnings}
    pending = [f for f in result.figures if not f.approved]
    if result.figures:
        response["figures"] = [
            {"figure": f.as_dict()["label"], "key": f.key, "kind": f.kind, "caption": f.caption, "png": f.png,
             "digest": f.digest, "approved": f.approved, "issues": f.issues}
            for f in result.figures
        ]
    if pending:
        response["action_required"] = (
            f"{len(pending)} generated figure(s) need the student's approval. Show each PNG to the student with "
            "the issues listed, fix what they ask for, and call approve_figures only after they explicitly approve."
        )
    figs = build_opts.figures_dir
    if figs.is_dir() and any(figs.iterdir()):
        response["figures_folder"] = str(figs)
    if profile.missing():
        response["warnings"].append(f"Cover is missing {', '.join(profile.missing())}; call set_profile to store them.")
    if export_pdf:
        try:
            response["pdf"] = str(export.to_pdf(result.path))
        except Exception as exc:
            response["warnings"].append(f"PDF export failed: {exc}")
    return response


# --------------------------------------------------------------------------- plan-first workflow


def _elicitation_supported(ctx: Context) -> bool:
    try:
        caps = ctx.client_capabilities
        return bool(caps is not None and getattr(caps, "elicitation", None) is not None)
    except Exception:
        return False


async def _ask_with_form(ctx: Context, plan: "planning.Plan") -> bool:
    """Show the checklist as a real form (tick boxes) when the client supports MCP elicitation."""
    fields: dict = {}
    for key, label, default in planning.REQUIREMENTS:
        fields[key] = (bool, Field(default=plan.requirements.get(key, default), title=label, description=label))
    for key, val in plan.settings.items():
        typ = type(val) if isinstance(val, (bool, float, int)) else str
        help_ = planning.SETTING_HELP[key]
        fields[f"setting_{key}"] = (typ, Field(default=val, title="Default: " + help_.split(":")[0], description=help_))
    for q in plan.open_questions:
        fields[f"answer_{q['key']}"] = (str, Field(default=plan.answers.get(q["key"], ""), title=q["question"], description=q["question"]))
    Form = create_model("AssignmentRequirements", **fields)
    try:
        result = await ctx.elicit("Tick what this assignment needs, change any defaults, and answer the questions.", Form)
    except Exception:
        return False
    if getattr(result, "action", "") != "accept" or result.data is None:
        return False
    data = result.data.model_dump()
    for key, _, _ in planning.REQUIREMENTS:
        plan.requirements[key] = bool(data.get(key, plan.requirements.get(key)))
    for key in list(plan.settings):
        if f"setting_{key}" in data:
            plan.settings[key] = data[f"setting_{key}"]
    for q in list(plan.open_questions):
        ans = str(data.get(f"answer_{q['key']}", "")).strip()
        if ans:
            plan.answers[q["key"]] = ans
    plan.open_questions = [q for q in plan.open_questions if q["key"] not in plan.answers]
    plan.history.append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": "form answered"})
    planning.save(plan)
    return True


@mcp.tool()
async def start_assignment(request: str, ctx: Context, template: str = "", brief_path: str = "") -> dict:
    """FIRST STEP for any new assignment, lab report or CA report. Call it as soon as the student describes
    the task, before writing anything. It creates a plan and returns a requirements checklist (tick boxes),
    the current defaults (page border, page numbers, tables, ...) and every open question.

    request: the student's request in their words. template: assignment | lab_report | ca_report if known.
    brief_path: the brief / lab sheet, if given (module, title, due date and questions are pre-filled).
    If the app supports forms, the checklist is shown to the student directly."""
    plan = planning.new_plan(request, template)
    detected = {}
    if brief_path:
        try:
            b = ingest.parse_brief(ingest.read_text(brief_path).text)
            detected = {"module": f"{b.module_code} – {b.module_name}".strip(" –") if b.module_code else "",
                        "title": b.title, "submission_date": b.due_date,
                        "questions_found": [f"{q['number']}. {q['text'][:120]}" for q in b.questions]}
            plan.answers.update({k: v for k, v in detected.items() if k in ("module", "title", "submission_date") and v})
            plan.answers["brief"] = brief_path
        except Exception as exc:
            detected = {"brief_error": str(exc)}
    plan.open_questions = [q for q in plan.open_questions if q["key"] not in plan.answers]
    planning.save(plan)

    form_used = _elicitation_supported(ctx) and await _ask_with_form(ctx, plan)
    plan = planning.load(plan.id)
    return {
        "plan_id": plan.id,
        "form_answered_by_student": form_used,
        "checklist": planning.checklist_markdown(plan),
        "open_questions": [q["question"] for q in plan.open_questions],
        "detected_from_brief": detected,
        "instruction": (
            "STOP. Do not write the document yet. "
            + ("The student filled in the form; confirm the remaining open questions (if any). " if form_used else
               "Show the student the checklist above exactly as tick boxes, list the defaults and ask if any should "
               "change, and ask ALL the open questions in ONE message. ")
            + "Add your own questions if the brief is ambiguous. Wait for the reply, then draft a rough plan "
            "(the steps you will take) and call save_plan."
        ),
    }


@mcp.tool()
def save_plan(
    plan_id: str,
    steps: list[str],
    requirements: dict | None = None,
    settings: dict | None = None,
    answers: dict | None = None,
    still_unanswered: list[str] | None = None,
    sections: list[str] | None = None,
    input_sections: list[str] | None = None,
) -> dict:
    """Save the student's ticked requirements, changed defaults, answers and a rough step-by-step plan, then
    show the plan to the student for approval.

    steps: short ordered steps, e.g. ["Read brief and notes", "Answer Q1 with block diagram", "Answer Q2
    calculation", "Review figures with student", "References + pre-submission check", "Export PDF"].
    requirements: {key: true/false} from the checklist. settings: changed defaults, e.g.
    {"border_width_pt": 1.5, "page_numbers": "bottom-right"}. answers: {"module": ..., "title": ...}.
    still_unanswered: questions you still need answered (the plan cannot be approved until they are).
    sections: every section / question the document will have, in order (e.g. ["Aim", "Theory", "Result",
        "Discussion", "Conclusion"] or the brief's questions). They are shown with "get my input here" tick boxes.
    input_sections: the sections the STUDENT ticked for their own input. Leave out the first time to show
        the suggested ticks (results, observations, procedure, discussion, conclusion, code, calculations)."""
    plan = planning.load(plan_id)
    if requirements:
        plan.requirements.update({k: bool(v) for k, v in requirements.items()})
    if settings:
        unknown = [k for k in settings if k not in planning.DEFAULT_SETTINGS]
        if unknown:
            return {"error": f"Unknown settings {unknown}. Allowed: {list(planning.DEFAULT_SETTINGS)}"}
        plan.settings.update(settings)
    if answers:
        plan.answers.update({k: str(v) for k, v in answers.items()})
    plan.open_questions = [{"key": f"extra{i}", "question": q} for i, q in enumerate(still_unanswered or [])]
    plan.steps = [{"n": i + 1, "title": t, "status": "pending", "note": ""} for i, t in enumerate(steps)]
    if sections:
        old = {planning._norm_title(x["title"]): x for x in plan.sections}
        new_sections = []
        for title in sections:
            suggested, questions = planning.section_profile(title)
            prev = old.get(planning._norm_title(title), {})
            new_sections.append({"title": title, "my_input": prev.get("my_input", suggested),
                                 "questions": questions, "input": prev.get("input", "")})
        plan.sections = new_sections
    if input_sections is not None:
        ticked = {planning._norm_title(t) for t in input_sections}
        for sec in plan.sections:
            sec["my_input"] = planning._norm_title(sec["title"]) in ticked
    plan.status = "gathering_requirements" if plan.open_questions else "awaiting_approval"
    plan.history.append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": "plan saved"})
    planning.save(plan)
    return {
        "plan_id": plan.id,
        "status": plan.status,
        "plan": planning.plan_markdown(plan),
        "instruction": (
            "Ask the remaining questions first." if plan.open_questions else
            "Show this plan to the student, including the 'get my input here' section ticks, and ask: which sections "
            "do you want to give your own input for, and do you approve the plan? Call save_plan again with "
            "input_sections if they change the ticks. Call approve_plan only after they clearly agree."
        ),
    }


@mcp.tool()
def approve_plan(plan_id: str, student_reply: str) -> dict:
    """Mark the plan approved. Call ONLY after the student has explicitly agreed to the plan.
    student_reply: the student's own words agreeing (e.g. "yes go ahead")."""
    plan = planning.load(plan_id)
    if not student_reply.strip():
        return {"error": "Quote the student's agreement in student_reply."}
    if plan.open_questions:
        return {"error": "There are unanswered questions: " + "; ".join(q["question"] for q in plan.open_questions)}
    if not plan.steps:
        return {"error": "The plan has no steps yet; call save_plan first."}
    plan.status = "approved"
    plan.history.append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": "approved", "student": student_reply})
    planning.save(plan)
    first = plan.steps[0]["title"]
    return {
        "status": "approved",
        "plan": planning.plan_markdown(plan),
        "instruction": f"Start step 1 ({first}). Call update_plan_step when it begins and when it is done, and "
        "check in with the student after every step.",
    }


@mcp.tool()
def update_plan_step(plan_id: str, step: int, status: Literal["in_progress", "done", "needs_changes"], note: str = "") -> dict:
    """Record progress on a plan step. After a step is done the student must be asked before continuing:
    tell them what was done, show the result (file, figure, section) and ask if it is OK or what to change."""
    plan = planning.load(plan_id)
    match = [s_ for s_ in plan.steps if s_["n"] == step]
    if not match:
        return {"error": f"No step {step}. Steps: " + ", ".join(f"{s_['n']}. {s_['title']}" for s_ in plan.steps)}
    match[0]["status"], match[0]["note"] = status, note
    if plan.status == "approved":
        plan.status = "in_progress"
    if all(s_["status"] == "done" for s_ in plan.steps):
        plan.status = "done"
    plan.history.append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": f"step {step} {status}", "note": note})
    planning.save(plan)
    nxt = next((s_ for s_ in plan.steps if s_["status"] != "done"), None)
    if status == "done":
        instruction = (f"CHECK-IN: tell the student step {step} is done ({match[0]['title']}), show what changed, and ask "
                       "whether they are happy or want changes. "
                       + (f"Only after they reply, continue with step {nxt['n']} ({nxt['title']})." if nxt else
                          "All steps are done. Ask if anything else is needed before finishing."))
    elif status == "needs_changes":
        instruction = "Make the changes the student asked for, then mark the step done again and check in."
    else:
        instruction = "Work on this step, then mark it done and check in with the student."
    return {"plan": planning.plan_markdown(plan), "status": plan.status, "instruction": instruction}


@mcp.tool()
def ask_section_input(plan_id: str, section: str) -> dict:
    """Before writing a section the student ticked "get my input here": returns the questions to ask them
    (their real results, observations, problems hit, own conclusions...). Ask them, wait for the answers,
    then call save_section_input. Do not write the section from your own assumptions."""
    plan = planning.load(plan_id)
    sec = planning.find_section(plan, section)
    if sec is None:
        _tick, questions = planning.section_profile(section)
        sec = {"title": section, "my_input": True, "questions": questions, "input": ""}
        plan.sections.append(sec)
        planning.save(plan)
    return {
        "section": sec["title"],
        "questions": sec["questions"],
        "already_given": sec.get("input", ""),
        "instruction": "Ask the student these questions (add any specific to this assignment) in one message and "
        "wait. Rough notes or bullet points are fine. Then call save_section_input with their words.",
    }


@mcp.tool()
def save_section_input(plan_id: str, section: str, student_input: str) -> dict:
    """Store the student's own input for a section, word for word (their results, observations, problems,
    opinions). The section must then be written AROUND these points: keep their numbers, details and
    reasoning, use their phrasing where it reads well, and never invent results they did not give."""
    plan = planning.load(plan_id)
    if not student_input.strip():
        return {"error": "student_input is empty; ask the student first."}
    sec = planning.find_section(plan, section)
    if sec is None:
        _tick, questions = planning.section_profile(section)
        sec = {"title": section, "my_input": True, "questions": questions, "input": ""}
        plan.sections.append(sec)
    sec["input"] = (sec.get("input", "") + "\n" + student_input.strip()).strip()
    sec["my_input"] = True
    plan.history.append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": f"input for {sec['title']}"})
    planning.save(plan)
    return {
        "section": sec["title"],
        "saved": True,
        "instruction": "Write this section around the student's points (their data, problems and conclusions), "
        "then show it to them and ask if it matches what they meant.",
    }


@mcp.tool()
def get_plan(plan_id: str) -> dict:
    """Show a plan with its requirements, settings, answers, steps and progress."""
    plan = planning.load(plan_id)
    return {"plan": planning.plan_markdown(plan), "status": plan.status, "answers": plan.answers,
            "settings": plan.settings, "docx": plan.docx_path,
            "section_inputs": {x["title"]: x.get("input", "") for x in plan.sections if x.get("my_input")}}


@mcp.tool()
def create_document(
    template: Template,
    title: str,
    body_markdown: str,
    module: str = "",
    submission_date: str = "",
    assets_dir: str = "",
    filename: str = "",
    export_pdf: bool = False,
    references: list[dict] | None = None,
    figure_captions: bool = False,
    number_equations: bool = False,
    scientific_equations: bool = True,
    toc: bool = False,
    list_of_figures: bool = False,
    list_of_tables: bool = False,
    page_numbers: PageNumbers = "bottom-center",
    header_text: str = "",
    footer_text: str = "",
    table_style: Literal["grid", "shaded"] = "grid",
    border_width_pt: float = 0.5,
    border_style: Literal["single", "double", "thick-thin", "dotted", "dashed", "none"] = "single",
    title_font: str = "",
    name: str = "",
    reg_no: str = "",
    intake: str = "",
    department: str = "",
    members: list[dict] | None = None,
    plan_id: str = "",
    skip_planning: bool = False,
) -> dict:
    """Generate the formatted Word document (cover page + body) and save it. Defaults reproduce the master
    assignment format exactly; every extra (TOC, page numbers, captions) is opt-in.

    template: lab_report | ca_report | assignment.
    title: document title shown large on the cover, e.g. "Interfacing a 16x2 LCD with STM32 using I2C Protocol".
    body_markdown: the full content in Markdown, following get_writing_guide(template). No cover details.
        May contain ```plot / ```diagram / ```circuit blocks, [@key] citations and @fig:x cross-references.
    module: module code and name, e.g. "ET2263 – Embedded Systems" (shown in capitals on the cover).
    submission_date: DD/MM/YYYY; defaults to today.
    assets_dir: folder that relative image and data-file paths in the body are resolved against.
    filename: output file name without extension; defaults to "<reg no>_<title>".
    export_pdf: also save a PDF next to the .docx (MS Word on Windows refreshes all fields first).
    references: IEEE reference entries for this document, each {key, type, authors, title, ...}; merged with
        the saved reference library. Cite them in the body as [@key]. The numbered list is generated.
    figure_captions: caption every figure that has alt text ("Figure 1: ..."). Figures/tables with an
        {#fig:x}/{#tbl:x} label are always numbered.
    number_equations: number every display equation (1), (2), ... flush right (\\tag{n} / \\notag per equation).
    scientific_equations: ISO 80000-2 typesetting (upright descriptive subscripts and units). Leave on.
    toc / list_of_figures / list_of_tables: add these after the cover page (off in the master format).
    Generated figures (plot/diagram/circuit) start unapproved: review them with the student (see
    review_figures) before exporting.
    page_numbers: bottom-center (default) | bottom-right | none. The cover never shows a number.
    header_text / footer_text: optional running header/footer text on body pages.
    table_style: grid (default: plain Word Table Grid, black lines, no colours, bold header) | shaded
        (navy header with banded rows).
    border_width_pt / border_style: page border, default thin 0.5 pt single line (0 or "none" removes it).
    department: department/faculty lines for this cover only (newline between lines), e.g.
        "Faculty of Engineering\nDepartment of Mathematics". Defaults to the profile.
    members: group assignments: [{"name": "A B C Student", "reg_no": "D/ENG/EE/25/0000"}, ...] shown as a
        table on the cover instead of a single name.
    plan_id: the approved plan from start_assignment/save_plan/approve_plan. Required: the document is
        only written after the student has approved a plan. Settings agreed in the plan are applied.
    skip_planning: only if the student explicitly says to skip the planning step.
    title_font: override the cover title font (default Agency FB, as in the master).
    name / reg_no / intake: override the stored profile for this document only.
    """
    plan = None
    if plan_id:
        try:
            plan = planning.load(plan_id)
        except FileNotFoundError as exc:
            return {"error": str(exc)}
    if os.environ.get("KDOCS_MCP_REQUIRE_PLAN", "1") != "0" and not skip_planning:
        if plan is None or plan.status not in ("approved", "in_progress", "done"):
            return {
                "error": "No approved plan yet. Call start_assignment, show the student the requirements checklist "
                "and questions, save_plan with their answers, and approve_plan once they agree. Then call "
                "create_document with plan_id.",
                "plan_status": plan.status if plan else None,
            }
    if plan is not None:
        heads = [s_.title for s_ in project.sections(body_markdown)]
        missing = planning.missing_input(plan, heads)
        if missing:
            return {
                "error": "These sections are ticked 'get my input here' but the student's input has not been "
                "collected yet: " + ", ".join(missing) + ". Use ask_section_input / save_section_input first "
                "(or write only the other sections for now).",
                "missing_input": missing,
            }
    if plan is not None:  # settings the student agreed in the plan win over untouched defaults
        st = plan.settings
        defaults = {"page_numbers": "bottom-center", "table_style": "grid", "border_width_pt": 0.5, "border_style": "single",
                    "number_equations": False, "figure_captions": False, "toc": False}
        given = {"page_numbers": page_numbers, "table_style": table_style, "border_width_pt": border_width_pt,
                 "border_style": border_style, "number_equations": number_equations, "figure_captions": figure_captions, "toc": toc}
        merged = {k: (st[k] if k in st and given[k] == defaults[k] else given[k]) for k in defaults}
        page_numbers, table_style = merged["page_numbers"], merged["table_style"]
        border_width_pt, border_style = float(merged["border_width_pt"]), merged["border_style"]
        number_equations, figure_captions, toc = merged["number_equations"], merged["figure_captions"], merged["toc"]
    src = DocSource(
        template=template,
        title=title,
        body_markdown=body_markdown,
        module=module,
        submission_date=submission_date or dt.date.today().strftime("%d/%m/%Y"),
        assets_dir=assets_dir,
        filename=filename,
        name=name,
        reg_no=reg_no,
        intake=intake,
        references=list(references or []),
        options={
            "figure_captions": figure_captions,
            "number_equations": number_equations,
            "scientific_equations": scientific_equations,
            "toc": toc,
            "list_of_figures": list_of_figures,
            "list_of_tables": list_of_tables,
            "page_numbers": page_numbers,
            "header_text": header_text,
            "footer_text": footer_text,
            "title_font": title_font,
            "table_style": table_style,
            "border_width_pt": border_width_pt,
            "border_style": border_style,
            "department": department,
            "members": list(members or []),
            "plan_id": plan_id,
        },
    )
    result = _build(src, export_pdf)
    if plan is not None:
        plan.docx_path = result["docx"]
        plan.status = "in_progress" if plan.status == "approved" else plan.status
        plan.history.append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": "document created", "docx": result["docx"]})
        planning.save(plan)
        result["next"] = ("Mark the step done with update_plan_step, tell the student what was produced, then review "
                          "the figures with them (review_figures) before moving on.")
    return result


# --------------------------------------------------------------------------- editing existing documents


def _rebuild(
    docx_path: str,
    src: DocSource,
    export_pdf: bool,
    note: str,
    live_op=None,
    overwrite_manual_edits: bool = False,
) -> dict:
    """Apply an edit. If the document is open in Word (Windows), the change goes straight into the open
    document (live_op). Otherwise the .docx is rebuilt, but never over hand edits made in Word unless the
    student agreed (overwrite_manual_edits)."""
    path = Path(docx_path).expanduser()
    doc = live_word.find_open_document(path)
    if doc is not None:
        if live_op is None:
            return {"error": "This change affects the whole document (cover or page settings), which cannot be "
                    "applied to a document that is open in Word. Ask the student to save and close it, then try again."}
        tmpdir = Path(tempfile.mkdtemp())
        try:
            built = _build(DocSource(**{**src.__dict__}), out_path=tmpdir / path.name)
            if not live_op(doc, Path(built["docx"])):
                return {"error": "Could not find that part of the document in Word (it may have been renamed by hand). "
                        "Ask the student to close the document so it can be rebuilt instead."}
            live_word.finish(doc)
            tmp_figs, real_figs = tmpdir / f"{path.stem}_figures", path.parent / f"{path.stem}_figures"
            if tmp_figs.is_dir():
                shutil.copytree(tmp_figs, real_figs, dirs_exist_ok=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        src.built_hash = project.file_hash(path)
        save_source(path, src)
        out = {"docx": str(path), "live": True, "change": note + " Applied live in Word (other hand edits kept).",
               "warnings": built["warnings"]}
        for key in ("figures", "action_required"):
            if key in built:
                out[key] = built[key]
        if export_pdf:
            pdf = path.with_suffix(".pdf")
            doc.ExportAsFixedFormat(str(pdf.resolve()), 17)
            out["pdf"] = str(pdf)
        return out
    if path.is_file() and src.built_hash and project.file_hash(path) != src.built_hash and not overwrite_manual_edits:
        return {
            "error": "This document was edited in Word after it was generated. Rebuilding would discard those hand "
            "edits. Ask the student: (a) open it in Word (open_in_word) so the change is applied live and their edits "
            "are kept, or (b) confirm the hand edits can be discarded, then repeat with overwrite_manual_edits=true.",
            "manual_edits_detected": True,
        }
    out = _build(src, export_pdf, out_path=path)
    out["change"] = note
    return out


@mcp.tool()
def open_in_word(docx_path: str) -> dict:
    """Open the document in Microsoft Word (Windows) so that later edits (update_section, insert_section,
    delete_section, replace_text) are applied live in the open window, keeping any hand edits."""
    path = Path(docx_path).expanduser()
    if not path.is_file():
        return {"error": f"File not found: {docx_path}"}
    try:
        live_word.open_document(path)
    except Exception as exc:
        return {"error": f"Could not open Word: {exc}. Live editing needs Microsoft Word on Windows (2013 or later)."}
    return {"opened": str(path), "live_editing": True}


def _input_gate(src: DocSource, headings: list[str]) -> dict | None:
    pid = src.options.get("plan_id")
    if not pid:
        return None
    try:
        plan = planning.load(pid)
    except FileNotFoundError:
        return None
    missing = planning.missing_input(plan, headings)
    if missing:
        return {"error": "Collect the student's own input first (ask_section_input / save_section_input) for: "
                + ", ".join(missing), "missing_input": missing}
    return None


@mcp.tool()
def get_document_source(docx_path: str) -> dict:
    """Show the editable source of a document made by this server: settings, section outline and Markdown body.
    Use before editing, so changes target the right section."""
    src = load_source(docx_path)
    return {
        "template": src.template,
        "title": src.title,
        "module": src.module,
        "submission_date": src.submission_date,
        "options": src.options,
        "outline": project.outline(src.body_markdown),
        "body_markdown": src.body_markdown,
        "references": src.references,
    }


@mcp.tool()
def update_section(docx_path: str, section: str, new_markdown: str, export_pdf: bool = False,
                   overwrite_manual_edits: bool = False) -> dict:
    """Replace one section (with its sub-sections) and rebuild the document; everything else is untouched.

    section: heading text ("Discussion", "Working Principle"), its position in the outline ("3"), or a
        question number for assignments ("Q2").
    new_markdown: the new content. If it does not start with a heading, the existing heading is kept.
    If the document is open in Word, the change is applied live there (hand edits elsewhere are kept).
    overwrite_manual_edits: only after the student agrees to lose edits they made by hand in Word.
    """
    src = load_source(docx_path)
    blocked = _input_gate(src, [section] + [s_.title for s_ in project.sections(new_markdown)])
    if blocked:
        return blocked
    old_title = project.find_section(src.body_markdown, section).title
    src.body_markdown = project.replace_section(src.body_markdown, section, new_markdown)
    new_heads = project.sections(new_markdown)
    new_title = new_heads[0].title if new_heads and new_markdown.lstrip().startswith("#") else old_title

    def live(doc, built):
        return live_word.replace_section_live(doc, old_title, built, new_title)

    return _rebuild(docx_path, src, export_pdf, f"Replaced section '{section}'.", live, overwrite_manual_edits)


@mcp.tool()
def insert_section(docx_path: str, new_markdown: str, after: str = "", before: str = "", export_pdf: bool = False,
                   overwrite_manual_edits: bool = False) -> dict:
    """Insert new content (e.g. an extra question or a 'Discussion' section) and rebuild.
    Give after= or before= a heading / outline number / "Q3"; with neither, it is added at the end
    (before References)."""
    src = load_source(docx_path)
    blocked = _input_gate(src, [s_.title for s_ in project.sections(new_markdown)])
    if blocked:
        return blocked
    after_t = project.find_section(src.body_markdown, after).title if after else None
    before_t = project.find_section(src.body_markdown, before).title if before else None
    src.body_markdown = project.insert_section(src.body_markdown, new_markdown, after or None, before or None)
    new_heads = project.sections(new_markdown)
    if not new_heads:
        return {"error": "new_markdown must start with a heading (e.g. '# Discussion')."}

    def live(doc, built):
        return live_word.insert_section_live(doc, built, new_heads[0].title, after_t, before_t)

    return _rebuild(docx_path, src, export_pdf, "Inserted new section.", live, overwrite_manual_edits)


@mcp.tool()
def delete_section(docx_path: str, section: str, export_pdf: bool = False, overwrite_manual_edits: bool = False) -> dict:
    """Remove a section (with its sub-sections) and rebuild (or delete it live if the document is open in Word)."""
    src = load_source(docx_path)
    title = project.find_section(src.body_markdown, section).title
    src.body_markdown = project.delete_section(src.body_markdown, section)

    def live(doc, built):
        return live_word.delete_section_live(doc, title)

    return _rebuild(docx_path, src, export_pdf, f"Deleted section '{section}'.", live, overwrite_manual_edits)


@mcp.tool()
def replace_text(docx_path: str, find: str, replace: str, count: int = 0, export_pdf: bool = False,
                 overwrite_manual_edits: bool = False) -> dict:
    """Find-and-replace in the document body (e.g. fix a value or a typo everywhere), then rebuild, or run
    it inside Word if the document is open there. count=0 replaces every occurrence."""
    src = load_source(docx_path)
    src.body_markdown, n = project.replace_text(src.body_markdown, find, replace, count)
    if n == 0:
        return {"docx": docx_path, "warnings": [f"'{find}' was not found; nothing changed."]}

    def live(doc, built):
        return live_word.replace_text_live(doc, find, replace, count) > 0

    return _rebuild(docx_path, src, export_pdf, f"Replaced {n} occurrence(s).", live, overwrite_manual_edits)


@mcp.tool()
def update_document_settings(
    docx_path: str,
    title: str | None = None,
    module: str | None = None,
    submission_date: str | None = None,
    template: Template | None = None,
    assets_dir: str | None = None,
    references: list[dict] | None = None,
    figure_captions: bool | None = None,
    number_equations: bool | None = None,
    toc: bool | None = None,
    list_of_figures: bool | None = None,
    list_of_tables: bool | None = None,
    page_numbers: PageNumbers | None = None,
    header_text: str | None = None,
    footer_text: str | None = None,
    table_style: Literal["grid", "shaded"] | None = None,
    border_width_pt: float | None = None,
    border_style: Literal["single", "double", "thick-thin", "dotted", "dashed", "none"] | None = None,
    department: str | None = None,
    members: list[dict] | None = None,
    export_pdf: bool = False,
    overwrite_manual_edits: bool = False,
) -> dict:
    """Change the cover details or document options (only the fields given) and rebuild. Needs the document
    to be closed in Word."""
    src = load_source(docx_path)
    for key, val in dict(title=title, module=module, submission_date=submission_date, template=template, assets_dir=assets_dir).items():
        if val is not None:
            setattr(src, key, val)
    if references is not None:
        src.references = list(references)
    for key, val in dict(
        figure_captions=figure_captions, number_equations=number_equations, toc=toc, list_of_figures=list_of_figures,
        list_of_tables=list_of_tables, page_numbers=page_numbers, header_text=header_text, footer_text=footer_text,
        table_style=table_style, border_width_pt=border_width_pt, border_style=border_style,
        department=department, members=members,
    ).items():
        if val is not None:
            src.options[key] = val
    return _rebuild(docx_path, src, export_pdf, "Settings updated.", None, overwrite_manual_edits)


def _figure_status(docx_path: str) -> tuple[DocSource, list[dict]]:
    """Current generated figures with critique and approval state. Builds into a scratch copy so the
    student's .docx is not touched; PNG paths point at the document's own figures folder."""
    src = load_source(docx_path)
    real = Path(docx_path).expanduser()
    tmpdir = Path(tempfile.mkdtemp())
    try:
        figures = _build(DocSource(**{**src.__dict__}), out_path=tmpdir / real.name).get("figures", [])
        keep = real.parent / f"{real.stem}_figures"
        keep.mkdir(exist_ok=True)
        for f in figures:  # keep the preview images next to the document
            target = keep / Path(f["png"]).name
            shutil.copyfile(f["png"], target)
            f["png"] = str(target)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return src, figures


@mcp.tool()
def review_figures(docx_path: str) -> dict:
    """Critically review every generated figure (plots, block diagrams, flowcharts, circuits) before the
    student approves it. Returns, for each figure, the PNG to show the student, an automatic critique
    (missing axis units, unreadable text size, unlabelled components or branches, no caption, never
    referred to in the text, ...) and whether it is approved.

    How to use: look at each PNG yourself and add your own critical judgement (is it technically
    correct? does it answer the question? is anything misleading or cluttered?). Present the image and
    all issues to the student, fix what they ask for with update_section, and call approve_figures only
    when the student says the figure is OK."""
    _src, figures = _figure_status(docx_path)
    pending = [f["figure"] for f in figures if not f["approved"]]
    return {
        "figures": figures,
        "pending": pending,
        "all_approved": not pending,
        "instruction": "Never approve on the student's behalf. Ask them about each pending figure.",
    }


@mcp.tool()
def approve_figures(docx_path: str, figures: list[str]) -> dict:
    """Record the STUDENT's approval of generated figures. Call only after the student explicitly approves.
    figures: e.g. ["Figure 1", "fig:transfer"] or ["all"]. If a figure is changed later it becomes pending
    again and needs a fresh approval."""
    src, current = _figure_status(docx_path)
    wanted = {f.strip().lower() for f in figures}
    approved = []
    for f in current:
        if "all" in wanted or {f["figure"].lower(), f["key"].lower()} & wanted:
            src.approvals[f["key"]] = f["digest"]
            approved.append(f["figure"])
    save_source(Path(docx_path).expanduser(), src)
    still = [f["figure"] for f in current if f["figure"] not in approved and not f["approved"]]
    return {"approved": approved, "still_pending": still}


@mcp.tool()
def export_pdf(docx_path: str, force: bool = False) -> dict:
    """Save a PDF of a document. On Windows with MS Word, Word refreshes the table of contents, figure
    numbers and cross-references first (and saves them into the .docx). Refuses while generated
    figures are still awaiting the student's approval, unless force=True (only if the student insists)."""
    path = Path(docx_path).expanduser()
    if not force:
        try:
            _src, figs = _figure_status(docx_path)
            pending = [f["figure"] for f in figs if not f["approved"]]
            if pending:
                return {"error": "Figures not yet approved by the student: " + ", ".join(pending)
                        + ". Run review_figures, get approval, then export again."}
        except FileNotFoundError:
            pass
    try:
        pdf = export.to_pdf(path)
        return {"pdf": str(pdf), "pages": export.page_count(pdf)}
    except Exception as exc:
        return {"error": str(exc)}


# --------------------------------------------------------------------------- source material


@mcp.tool()
def read_source(path: str, pages: str = "", max_chars: int = 40000) -> dict:
    """Read the text of a PDF, Word file, spreadsheet, text or code file (assignment brief, lecture notes,
    datasheet, previous report, source code). pages: e.g. "1-5" or "3" for PDFs. Long text is cut at
    max_chars; read further pages in another call."""
    try:
        st = ingest.read_text(path)
    except Exception as exc:
        return {"error": str(exc)}
    chosen = st.pages
    if pages and len(st.pages) > 1:
        idx: list[int] = []
        for part in pages.split(","):
            a, _, b = part.strip().partition("-")
            lo, hi = int(a), int(b or a)
            idx.extend(range(lo, hi + 1))
        chosen = [st.pages[i - 1] for i in idx if 1 <= i <= len(st.pages)]
    text = "\n\n".join(chosen)
    return {
        "path": str(st.path),
        "total_pages": len(st.pages),
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


@mcp.tool()
def extract_assignment_brief(path: str) -> dict:
    """Read an assignment/lab brief (PDF, DOCX or text) and pull out the module code and name, title, due
    date, instructions and each question with its parts and marks, ready to answer with the
    assignment template (one '# heading' per question)."""
    try:
        st = ingest.read_text(path)
    except Exception as exc:
        return {"error": str(exc)}
    b = ingest.parse_brief(st.text)
    return {
        "module": f"{b.module_code} – {b.module_name}".strip(" –") if b.module_code else "",
        "title": b.title,
        "due_date": b.due_date,
        "instructions": b.instructions,
        "questions": b.questions,
        "note": "Check the questions against the original; the full text is available via read_source.",
    }


@mcp.tool()
def spreadsheet_to_table(path: str, sheet: str = "", columns: list[str] | None = None, max_rows: int = 60, decimals: int | None = None) -> dict:
    """Turn an Excel (.xlsx) or CSV file of readings/results into a Markdown table for the body. It is
    rendered as a plain Word grid table. columns: optional subset/order of column headers."""
    try:
        md = ingest.table_to_markdown(path, sheet or None, columns, max_rows, decimals)
    except Exception as exc:
        return {"error": str(exc)}
    return {"markdown": md}


# --------------------------------------------------------------------------- visuals


def _preview_dir() -> Path:
    d = load_profile().out_dir() / "previews"
    d.mkdir(parents=True, exist_ok=True)
    return d


@mcp.tool()
def make_plot(spec: dict, filename: str = "", base_dir: str = "") -> dict:
    """Draw an engineering graph and save it as PNG (to preview, or to insert with ![...](path)).
    The same spec can be placed directly in the body as a ```plot block (YAML or JSON).

    spec: {type: line|scatter|step|stem|bar, x_label, y_label, title?, xscale/yscale: linear|log,
      xlim, ylim, grid, legend_loc, constants: {name: value},
      series: [ {label, x: [...], y: [...]}  |  {label, expr: "2*Tm*s*sm/(s^2+sm^2)", var: "s",
                range: [0, 1], points}  |  {label, file: "data.xlsx", x: "Time (s)", y: "Current (A)"} ],
      hlines: [{y, label}], vlines: [{x, label}], annotations: [{x, y, text}]}
    Labels may use $...$ maths, e.g. "$V_{out}$ (V)". Formulas allow + - * / ^, sin, cos, exp, log, sqrt, pi...
    """
    from .plots import make_plot as _mk

    out = _preview_dir() / f"{_slug(filename or 'plot')}.png"
    try:
        _mk(spec, out, base_dir=Path(base_dir).expanduser() if base_dir else None)
    except Exception as exc:
        return {"error": str(exc)}
    return {"png": str(out), "markdown": f"![]({out.as_posix()}){{width=85%}}"}


@mcp.tool()
def make_diagram(mermaid: str, filename: str = "") -> dict:
    """Draw a block diagram or flowchart from Mermaid flowchart syntax, e.g.
    'flowchart LR\\n A[Input Register] --> B[Switching Network] -->|I_sum| C((Op-Amp))'.
    Shapes: [box] (rounded) {decision} ((circle)) [/input-output/]. Edge labels: -->|text| or -- text -->.
    Feedback loops are routed around the outside. Can also be written in the body as a ```diagram block."""
    from .diagrams import render_flowchart

    out = _preview_dir() / f"{_slug(filename or 'diagram')}.png"
    try:
        render_flowchart(mermaid, out)
    except Exception as exc:
        return {"error": str(exc)}
    return {"png": str(out), "markdown": f"![]({out.as_posix()})"}


@mcp.tool()
def make_circuit(elements: list[dict], filename: str = "") -> dict:
    """Draw a circuit or logic diagram (schemdraw), placing elements one after another.
    Each element: {type, dir: right|left|up|down, len, label, value, label_loc: top|bot|left|right,
      id, at: "id.anchor", to/tox/toy: "id.anchor", anchor, flip, reverse, push, pop, inputs}.
    Types: resistor, capacitor, inductor, vsource, isource, ac, battery, ground, opamp (anchors in1, in2,
      out), diode, led, zener, switch, npn/pnp (base, collector, emitter), nmos/pmos, dot, line, gap,
      lamp, motor, meter, and, or, not, nand, nor, xor (anchors in1, in2, out).
    Labels may use $...$ maths. Can also be written in the body as a ```circuit block (YAML list)."""
    from .diagrams import render_circuit

    out = _preview_dir() / f"{_slug(filename or 'circuit')}.png"
    try:
        render_circuit(elements, out)
    except Exception as exc:
        return {"error": str(exc)}
    return {"png": str(out), "markdown": f"![]({out.as_posix()}){{width=70%}}"}


# --------------------------------------------------------------------------- references


@mcp.tool()
def lookup_reference(identifier: str, key: str = "", save: bool = True) -> dict:
    """Create an IEEE reference from a DOI, ISBN or web link (via Crossref / Open Library / the page) and
    save it to the reference library. Cite it in any document as [@key]."""
    try:
        entry = references.lookup(identifier)
    except Exception as exc:
        return {"error": f"Lookup failed ({exc}). Add it manually with add_reference."}
    lib = references.load_library()
    key = key or references.make_key(entry, set(lib))
    if save:
        lib[key] = entry
        references.save_library(lib)
    return {"key": key, "entry": entry, "ieee": references.to_plain(references.format_ieee(entry)), "saved": save}


@mcp.tool()
def add_reference(
    key: str,
    title: str,
    type: Literal["article", "book", "chapter", "inproceedings", "preprint", "web", "datasheet", "manual", "lecture", "report", "thesis", "standard"] = "web",
    authors: list[str] | None = None,
    organization: str = "",
    journal: str = "",
    booktitle: str = "",
    publisher: str = "",
    address: str = "",
    edition: str = "",
    volume: str = "",
    number: str = "",
    pages: str = "",
    year: int | None = None,
    month: int | None = None,
    doi: str = "",
    url: str = "",
    accessed: str = "",
    eprint: str = "",
) -> dict:
    """Save a reference (book, paper, preprint, datasheet, website, lecture notes...) to the library for [@key] citations.
    For arXiv preprints use type="preprint" and eprint="arXiv:2506.23425".
    authors: ["Behzad Razavi", ...]. accessed: YYYY-MM-DD for web sources (defaults to today when url is set)."""
    entry = {k: v for k, v in dict(
        type=type, authors=authors or [], organization=organization, journal=journal, booktitle=booktitle,
        publisher=publisher, address=address, edition=edition, volume=volume, number=number, pages=pages,
        year=year, month=month, doi=doi, url=url, title=title, eprint=eprint,
        accessed=accessed or (dt.date.today().isoformat() if url else ""),
    ).items() if v not in ("", None, [])}
    lib = references.load_library()
    lib[key] = entry
    references.save_library(lib)
    return {"key": key, "ieee": references.to_plain(references.format_ieee(entry))}


@mcp.tool()
def list_references() -> list[dict]:
    """List the saved reference library (key and IEEE-formatted text)."""
    return [{"key": k, "ieee": references.to_plain(references.format_ieee(e))} for k, e in references.load_library().items()]


@mcp.tool()
def remove_reference(key: str) -> dict:
    """Delete a reference from the library."""
    lib = references.load_library()
    existed = lib.pop(key, None) is not None
    references.save_library(lib)
    return {"removed": existed}


# --------------------------------------------------------------------------- quality checks


@mcp.tool()
def check_document(
    docx_path: str,
    word_limit: int | None = None,
    page_limit: int | None = None,
    brief_path: str = "",
) -> dict:
    """Pre-submission check. Reports placeholders left in, spelling mistakes and typos, repeated words,
    numbers without a space before the unit, first-person writing, empty sections, missing images,
    broken citations and cross-references, figures never referred to, missing lab sections, unanswered
    questions (compared with brief_path) and word/page limits. Fix errors before submitting."""
    path = Path(docx_path).expanduser()
    if not path.is_file():
        return {"error": f"File not found: {docx_path}"}
    markdown, warnings, template = None, [], ""
    try:
        src = load_source(path)
        markdown, template = src.body_markdown, src.template
        tmp = Path(tempfile.mkdtemp()) / path.name
        built = _build(src, out_path=tmp)
        warnings = list(built["warnings"])
        for f in built.get("figures", []):
            for issue in f["issues"]:
                warnings.append(f"{f['figure']} ({f['kind']}): {issue}")
            if not f["approved"]:
                warnings.append(f"{f['figure']} ({f['kind']}) is not approved by the student yet (review_figures).")
        shutil.rmtree(tmp.parent, ignore_errors=True)
    except FileNotFoundError:
        pass
    pages = None
    if page_limit:
        try:
            tmpdir = Path(tempfile.mkdtemp())
            pages = export.page_count(export.to_pdf(path, out_dir=tmpdir))
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception as exc:
            warnings.append(f"Could not count pages: {exc}")
    expected = None
    if brief_path:
        try:
            expected = len(ingest.parse_brief(ingest.read_text(brief_path).text).questions) or None
        except Exception as exc:
            warnings.append(f"Could not read the brief: {exc}")
    report = quality.check_document(
        path, markdown, warnings, word_limit=word_limit, page_count=pages, page_limit=page_limit,
        expected_questions=expected, template=template,
    )
    if markdown is not None and src.options.get("plan_id"):
        try:
            plan = planning.load(src.options["plan_id"])
            heads = [s_.title for s_ in project.sections(markdown)]
            ticked = [planning.find_section(plan, h) for h in heads]
            ticked = [t for t in ticked if t and t["my_input"]]
            given = [t["title"] for t in ticked if t.get("input")]
            report["summary"]["sections_from_student_input"] = f"{len(given)} of {len(ticked)} ticked sections"
            for t in ticked:
                if not t.get("input"):
                    report["issues"].insert(0, {"severity": "error", "where": t["title"],
                        "message": f"'{t['title']}' was ticked 'get my input here' but no input from the student was recorded."})
                    report["summary"]["errors"] += 1
                    report["summary"]["ready_to_submit"] = False
        except FileNotFoundError:
            pass
    return report


@mcp.tool()
def check_similarity(docx_path: str, sources: list[str], threshold_percent: int = 30) -> dict:
    """Compare the document with source files (lecture notes, papers, web pages saved as PDF/DOCX/TXT,
    a friend's report) and flag paragraphs that copy too closely (shared 6-word phrases). Not a
    replacement for Turnitin, but catches close paraphrasing before submission."""
    path = Path(docx_path).expanduser()
    texts = {}
    for s in sources:
        try:
            texts[Path(s).name] = ingest.read_text(s).text
        except Exception as exc:
            return {"error": f"Could not read {s}: {exc}"}
    return quality.similarity_report(path, texts, threshold=threshold_percent / 100)


def main() -> None:
    parser = argparse.ArgumentParser(description="KDocs MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="stdio for Claude Desktop; http (streamable HTTP at /mcp) for ChatGPT and other remote clients",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--allowed-host",
        action="append",
        default=[],
        help="extra Host header to accept, e.g. your tunnel domain (repeatable)",
    )
    args = parser.parse_args()
    if args.transport == "stdio":
        mcp.run()
        return
    security = None
    if args.allowed_host:
        local = [f"{h}:{args.port}" for h in ("127.0.0.1", "localhost")]
        hosts = local + [h for a in args.allowed_host for h in (a, f"{a}:*")]
        security = TransportSecuritySettings(
            allowed_hosts=hosts,
            allowed_origins=[f"https://{a}" for a in args.allowed_host] + [f"http://{h}" for h in local],
        )
    kwargs = dict(host=args.host, port=args.port, transport_security=security)
    mcp.run(transport="streamable-http" if args.transport == "http" else "sse", **kwargs)


if __name__ == "__main__":
    main()
