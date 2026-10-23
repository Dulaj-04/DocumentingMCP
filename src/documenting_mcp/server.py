"""MCP server: tools for generating KDU EE lab reports, CA reports and assignments as .docx/.pdf."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from . import export
from .builder import CoverInfo, build_report
from .guides import guide_for
from .profile import Profile, load_profile, save_profile
from .styles import TEMPLATES

Template = Literal["lab_report", "ca_report", "assignment"]
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf"}

mcp = MCPServer(
    "DocumentingMCP",
    instructions=(
        "Generates university engineering documents (lab reports, CA/simulation reports, Q&A assignments) "
        "as formatted Word files in the KDU EE house style. Workflow: (1) call get_profile; if name/reg_no/"
        "intake are missing, ask the student and call set_profile. (2) call get_writing_guide for the chosen "
        "template and follow it. (3) if the student has screenshots/photos, call list_files on their folder. "
        "(4) call create_document with the full Markdown body. Report the saved file path to the student."
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
    figure_captions: bool = False,
    title_font: str = "",
    name: str = "",
    reg_no: str = "",
    intake: str = "",
) -> dict:
    """Generate the formatted Word document (cover page + body) and save it.

    template: lab_report | ca_report | assignment.
    title: document title shown large on the cover, e.g. "Interfacing a 16x2 LCD with STM32 using I2C Protocol".
    body_markdown: the full content in Markdown, following get_writing_guide(template). No cover details.
    module: module code and name, e.g. "ET2263 – Embedded Systems" (shown in capitals on the cover).
    submission_date: DD/MM/YYYY; defaults to today.
    assets_dir: folder that relative image paths in the body are resolved against.
    filename: output file name without extension; defaults to "<reg no>_<title>".
    export_pdf: also save a PDF next to the .docx (needs MS Word on Windows, or LibreOffice).
    figure_captions: number figures and caption them with their alt text ("Figure 1: ...").
    title_font: override the cover title font (e.g. "Agency FB").
    name / reg_no / intake: override the stored profile for this document only.
    """
    style = TEMPLATES[template].with_overrides(
        figure_captions=figure_captions or None,
        title_font=title_font or None,
    )
    profile: Profile = load_profile()
    for key, val in dict(name=name, reg_no=reg_no, intake=intake).items():
        if val:
            setattr(profile, key, val)

    date = submission_date or dt.date.today().strftime("%d/%m/%Y")
    stem = filename or f"{_slug(profile.reg_no.split('/')[-1]) + '_' if profile.reg_no else ''}{_slug(title)}"
    out = profile.out_dir() / f"{_slug(stem)}.docx"
    assets = Path(assets_dir).expanduser() if assets_dir else None

    result = build_report(
        style=style,
        profile=profile,
        cover=CoverInfo(title=title.strip(), module=module.strip(), submission_date=date),
        markdown=body_markdown,
        out_path=out,
        assets_dir=assets,
    )
    response: dict = {"docx": str(result.path), "warnings": result.warnings}
    if profile.missing():
        response["warnings"].append(
            f"Cover is missing {', '.join(profile.missing())}; call set_profile to store them."
        )
    if export_pdf:
        try:
            response["pdf"] = str(export.to_pdf(result.path))
        except Exception as exc:
            response["warnings"].append(f"PDF export failed: {exc}")
    return response


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
