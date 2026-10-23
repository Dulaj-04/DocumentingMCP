"""Per-template style definitions, derived from docs/style-spec.md."""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class HeadingStyle:
    font: str
    size: float
    bold: bool = False
    underline: bool = False
    caps: bool = False
    align: str = "left"  # left | center
    space_before: float = 12
    space_after: float = 6


@dataclass(frozen=True)
class TemplateStyle:
    key: str
    label: str
    body_font: str
    body_size: float
    h1: HeadingStyle
    h2: HeadingStyle
    h3: HeadingStyle
    # Assignments number each top-level heading as a question ("1.", "2.", ...).
    number_h1: bool = False
    cover_font: str = "Times New Roman"
    title_font: str = "Times New Roman"
    title_size: float = 22
    code_font: str = "Consolas"
    code_size: float = 9.5
    figure_captions: bool = False
    table_header_bold: bool = False
    sections: tuple[str, ...] = field(default_factory=tuple)

    def with_overrides(self, **kw) -> "TemplateStyle":
        return replace(self, **{k: v for k, v in kw.items() if v is not None})


_TNR = "Times New Roman"

LAB_REPORT = TemplateStyle(
    key="lab_report",
    label="Lab report",
    body_font="Calibri",
    body_size=11.5,
    h1=HeadingStyle("Calibri", 14, underline=True, caps=True, align="center", space_before=24, space_after=12),
    h2=HeadingStyle("Calibri", 12.5, underline=True, space_before=12, space_after=6),
    h3=HeadingStyle("Calibri", 11.5, bold=True, space_before=10, space_after=4),
    sections=("Aim", "Apparatus", "Theory", "Procedure", "Observation", "Result", "Code", "Discussion", "Conclusion"),
)

CA_REPORT = TemplateStyle(
    key="ca_report",
    label="Continuous assessment / simulation report",
    body_font=_TNR,
    body_size=12,
    h1=HeadingStyle(_TNR, 16, bold=True, underline=True, space_before=18, space_after=8),
    h2=HeadingStyle(_TNR, 13, bold=True, space_before=12, space_after=6),
    h3=HeadingStyle(_TNR, 12, bold=True, space_before=10, space_after=4),
    sections=(
        "Objectives",
        "Given Data",
        "Assumptions Made",
        "Model Description",
        "Result and Observation",
        "Discussion",
        "Conclusion",
        "References",
    ),
)

ASSIGNMENT = TemplateStyle(
    key="assignment",
    label="Question-and-answer assignment",
    body_font=_TNR,
    body_size=12,
    h1=HeadingStyle(_TNR, 12, space_before=18, space_after=10),
    h2=HeadingStyle(_TNR, 12, bold=True, underline=True, space_before=12, space_after=6),
    h3=HeadingStyle(_TNR, 12, bold=True, space_before=10, space_after=4),
    number_h1=True,
    sections=("<one '#' heading per question>", "References"),
)

TEMPLATES: dict[str, TemplateStyle] = {t.key: t for t in (LAB_REPORT, CA_REPORT, ASSIGNMENT)}
