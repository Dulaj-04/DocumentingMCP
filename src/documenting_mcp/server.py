"""MCP server: tools for generating KDU EE lab reports, CA reports and assignments as .docx/.pdf."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from . import export, ingest, project, quality, references
from .builder import BuildOptions, CoverInfo, build_report
from .guides import guide_for
from .profile import Profile, load_profile, save_profile
from .project import DocSource, load_source, save_source
from .styles import TEMPLATES

Template = Literal["lab_report", "ca_report", "assignment"]
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf"}

mcp = MCPServer(
    "DocumentingMCP",
    instructions=(
        "Generates university engineering documents (lab reports, CA/simulation reports, Q&A assignments) "
        "as formatted Word files in the KDU EE house style (the master assignment format). Workflow: "
        "(1) get_profile; if name/reg_no/intake are missing, ask and call set_profile. "
        "(2) If the student has a brief, extract_assignment_brief; read lecture notes with read_source. "
        "(3) get_writing_guide for the template and follow it. "
        "(4) list_files for screenshots; use ```plot / ```diagram / ```circuit blocks for graphs, block "
        "diagrams and circuits; spreadsheet_to_table for data; lookup_reference/add_reference + [@key] for citations. "
        "(5) create_document with the full Markdown body. "
        "(6) check_document (and check_similarity against the notes) and fix issues with update_section / "
        "replace_text instead of regenerating. Report the saved file path to the student."
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

    name: as it should appear on the cover, e.g. "W M L M Herath".
    reg_no: e.g. "D/ENG/EE/25/0008".
    intake: e.g. "42".
    department: use a newline to control the line break on the cover.
    logo_path: optional custom crest image; the KDU crest is bundled by default.
    output_dir: folder where documents are saved (default: Documents/DocumentingMCP).
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
        page_numbers=opts.get("page_numbers") or "none",
        header_text=opts.get("header_text") or "",
        footer_text=opts.get("footer_text") or "",
    )
    result = build_report(
        style=style,
        profile=profile,
        cover=CoverInfo(title=src.title.strip(), module=src.module.strip(), submission_date=src.submission_date),
        markdown=src.body_markdown,
        out_path=out_path,
        assets_dir=assets,
        options=build_opts,
    )
    save_source(result.path, src)
    response: dict = {"docx": str(result.path), "warnings": result.warnings}
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
    page_numbers: PageNumbers = "none",
    header_text: str = "",
    footer_text: str = "",
    title_font: str = "",
    name: str = "",
    reg_no: str = "",
    intake: str = "",
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
    page_numbers: none (master) | bottom-center | bottom-right. The cover never shows a number.
    header_text / footer_text: optional running header/footer text on body pages.
    title_font: override the cover title font (default Agency FB, as in the master).
    name / reg_no / intake: override the stored profile for this document only.
    """
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
        },
    )
    return _build(src, export_pdf)


# --------------------------------------------------------------------------- editing existing documents


def _rebuild(docx_path: str, src: DocSource, export_pdf: bool, note: str) -> dict:
    out = _build(src, export_pdf, out_path=Path(docx_path).expanduser())
    out["change"] = note
    return out


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
def update_section(docx_path: str, section: str, new_markdown: str, export_pdf: bool = False) -> dict:
    """Replace one section (with its sub-sections) and rebuild the document; everything else is untouched.

    section: heading text ("Discussion", "Working Principle"), its position in the outline ("3"), or a
        question number for assignments ("Q2").
    new_markdown: the new content. If it does not start with a heading, the existing heading is kept.
    """
    src = load_source(docx_path)
    src.body_markdown = project.replace_section(src.body_markdown, section, new_markdown)
    return _rebuild(docx_path, src, export_pdf, f"Replaced section '{section}'.")


@mcp.tool()
def insert_section(docx_path: str, new_markdown: str, after: str = "", before: str = "", export_pdf: bool = False) -> dict:
    """Insert new content (e.g. an extra question or a 'Discussion' section) and rebuild.
    Give after= or before= a heading / outline number / "Q3"; with neither, it is added at the end
    (before References)."""
    src = load_source(docx_path)
    src.body_markdown = project.insert_section(src.body_markdown, new_markdown, after or None, before or None)
    return _rebuild(docx_path, src, export_pdf, "Inserted new section.")


@mcp.tool()
def delete_section(docx_path: str, section: str, export_pdf: bool = False) -> dict:
    """Remove a section (with its sub-sections) and rebuild."""
    src = load_source(docx_path)
    src.body_markdown = project.delete_section(src.body_markdown, section)
    return _rebuild(docx_path, src, export_pdf, f"Deleted section '{section}'.")


@mcp.tool()
def replace_text(docx_path: str, find: str, replace: str, count: int = 0, export_pdf: bool = False) -> dict:
    """Find-and-replace in the document body (e.g. fix a value or a typo everywhere), then rebuild.
    count=0 replaces every occurrence."""
    src = load_source(docx_path)
    src.body_markdown, n = project.replace_text(src.body_markdown, find, replace, count)
    if n == 0:
        return {"docx": docx_path, "warnings": [f"'{find}' was not found; nothing changed."]}
    return _rebuild(docx_path, src, export_pdf, f"Replaced {n} occurrence(s).")


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
    export_pdf: bool = False,
) -> dict:
    """Change the cover details or document options (only the fields given) and rebuild."""
    src = load_source(docx_path)
    for key, val in dict(title=title, module=module, submission_date=submission_date, template=template, assets_dir=assets_dir).items():
        if val is not None:
            setattr(src, key, val)
    if references is not None:
        src.references = list(references)
    for key, val in dict(
        figure_captions=figure_captions, number_equations=number_equations, toc=toc, list_of_figures=list_of_figures,
        list_of_tables=list_of_tables, page_numbers=page_numbers, header_text=header_text, footer_text=footer_text,
    ).items():
        if val is not None:
            src.options[key] = val
    return _rebuild(docx_path, src, export_pdf, "Settings updated.")


@mcp.tool()
def export_pdf(docx_path: str) -> dict:
    """Save a PDF of a document. On Windows with MS Word, Word refreshes the table of contents, figure
    numbers and cross-references first (and saves them into the .docx)."""
    path = Path(docx_path).expanduser()
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
    rendered in the master table style. columns: optional subset/order of column headers."""
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
    type: Literal["article", "book", "chapter", "inproceedings", "web", "datasheet", "manual", "lecture", "report", "thesis", "standard"] = "web",
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
) -> dict:
    """Save a reference (book, paper, datasheet, website, lecture notes...) to the library for [@key] citations.
    authors: ["Behzad Razavi", ...]. accessed: YYYY-MM-DD for web sources (defaults to today when url is set)."""
    entry = {k: v for k, v in dict(
        type=type, authors=authors or [], organization=organization, journal=journal, booktitle=booktitle,
        publisher=publisher, address=address, edition=edition, volume=volume, number=number, pages=pages,
        year=year, month=month, doi=doi, url=url, title=title,
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
        warnings = _build(src, out_path=tmp)["warnings"]
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
    return quality.check_document(
        path, markdown, warnings, word_limit=word_limit, page_count=pages, page_limit=page_limit,
        expected_questions=expected, template=template,
    )


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
    parser = argparse.ArgumentParser(description="DocumentingMCP server")
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
