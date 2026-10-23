"""Critical review of generated figures (plots, diagrams, circuits) before the student approves them.

Each generated figure gets a stable key (its #fig: label, or its position) and a content hash.
A figure counts as approved only while its content still matches the hash the student approved,
so any change to a figure sends it back for approval.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image

RENDER_DPI = 220
BASE_FONT_PT = {"plot": 10.5, "diagram": 11.0, "circuit": 11.0}
MIN_READABLE_PT = 8.0
_UNIT = re.compile(r"\(([^)]+)\)|\[[^\]]+\]|/\s*\w|\bin\s+\w+$")
_DIMENSIONLESS = re.compile(r"\b(code|count|iterations?|index|number|sample|step|ratio|slip|pu|per unit|%|db)\b", re.I)


@dataclass
class FigureRecord:
    key: str  # "fig:block" or "figure-3"
    number: int | None
    kind: str  # plot | diagram | circuit
    caption: str
    png: str
    digest: str
    display_width_in: float
    issues: list[str] = field(default_factory=list)
    approved: bool = False

    def as_dict(self) -> dict:
        d = asdict(self)
        d["label"] = f"Figure {self.number}" if self.number else self.key
        return d


def digest(kind: str, text: str, attrs: dict) -> str:
    raw = kind + "\n" + text.strip() + "\n" + repr(sorted(attrs.items()))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _effective_font(kind: str, png: Path, display_width_in: float) -> float:
    with Image.open(png) as im:
        natural_w = im.size[0] / RENDER_DPI
    scale = min(1.0, display_width_in / natural_w) if natural_w else 1.0
    return BASE_FONT_PT[kind] * scale


def critique(kind: str, text: str, attrs: dict, png: Path, display_width_in: float, referenced: bool) -> list[str]:
    """Return human-readable problems a lecturer could mark down. An empty list means none were found."""
    import yaml

    issues: list[str] = []
    eff = _effective_font(kind, png, display_width_in)
    if eff < MIN_READABLE_PT:
        issues.append(
            f"Text will print at about {eff:.1f} pt, which is too small to read comfortably. "
            + ("Use 'flowchart TD' (top-down), shorten the labels or split the diagram." if kind == "diagram"
               else "Make the figure wider or use fewer labels.")
        )
    if not attrs.get("caption"):
        issues.append("No caption. Add caption=\"...\" so the figure is numbered and explained.")
    if not referenced:
        issues.append("The figure is never referred to in the text. Mention it (e.g. 'as shown in @fig:x').")

    if kind == "plot":
        try:
            spec = yaml.safe_load(text) or {}
        except Exception as exc:  # already reported as a drawing error
            return issues + [f"Plot spec could not be read: {exc}"]
        series = spec.get("series") or [spec]
        for axis in ("x_label", "y_label"):
            label = str(spec.get(axis) or "")
            if not label and not (axis == "x_label" and spec.get("categories")):
                issues.append(f"Missing {axis.replace('_', ' ')}. Every axis needs a quantity and a unit.")
            elif label and not _UNIT.search(label) and not _DIMENSIONLESS.search(label):
                issues.append(f"Axis label '{label}' has no unit; write it as 'Quantity (unit)'.")
        if len(series) > 1 and not all(s.get("label") for s in series):
            issues.append("Several data series but not all have a legend label.")
        if spec.get("title"):
            issues.append("Plot has a title as well as a caption; remove the title (the caption does that job).")
        for s in series:
            if "x" in s and "y" in s and len(s["x"]) != len(s["y"]):
                issues.append(f"Series '{s.get('label', '?')}' has {len(s['x'])} x values but {len(s['y'])} y values.")
            if "y" in s and len(s["y"]) < 3 and spec.get("type", s.get("type")) not in ("bar",):
                issues.append(f"Series '{s.get('label', '?')}' has fewer than 3 points; a table may be clearer.")
        if spec.get("type") == "bar" and not spec.get("categories"):
            issues.append("Bar chart without 'categories'; the bars will be labelled with numbers only.")
    elif kind == "diagram":
        from .diagrams import parse_mermaid

        try:
            g = parse_mermaid(text)
        except Exception as exc:
            return issues + [f"Diagram could not be read: {exc}"]
        if len(g.nodes) > 12:
            issues.append(f"{len(g.nodes)} blocks is busy for one figure; consider grouping or splitting it.")
        connected = {e.src for e in g.edges} | {e.dst for e in g.edges}
        lonely = [n.label.replace("\n", " ") for n in g.nodes.values() if n.id not in connected]
        if lonely and len(g.nodes) > 1:
            issues.append("Blocks with no connection: " + ", ".join(lonely))
        long = [n.label.replace("\n", " ") for n in g.nodes.values() if max(len(x) for x in n.label.split("\n")) > 28]
        if long:
            issues.append("Very long block labels (use <br> or shorter wording): " + "; ".join(long[:3]))
        decisions = [n for n in g.nodes.values() if n.shape == "diamond"]
        for n in decisions:
            outs = [e for e in g.edges if e.src == n.id]
            if len(outs) >= 2 and not all(e.label for e in outs):
                issues.append(f"Decision '{n.label}' has unlabelled branches; label them (e.g. Yes / No).")
    elif kind == "circuit":
        try:
            spec = yaml.safe_load(text)
            items = spec.get("elements", spec) if isinstance(spec, dict) else spec
        except Exception as exc:
            return issues + [f"Circuit could not be read: {exc}"]
        parts = [i for i in items if isinstance(i, dict) and str(i.get("type", "")).lower() not in ("line", "wire", "dot", "gap", "ground", "gnd")]
        unlabelled = [str(i.get("type")) for i in parts if not i.get("label") and str(i.get("type")).lower() not in ("opamp", "and", "or", "not", "nand", "nor", "xor", "xnor", "buf")]
        if unlabelled:
            issues.append("Components without a name or value: " + ", ".join(unlabelled[:5]) + ". Label them (e.g. R1 = 10 kΩ).")
        if not any(str(i.get("type", "")).lower() in ("ground", "gnd") for i in items if isinstance(i, dict)):
            issues.append("No ground symbol; check that the reference node is shown.")
    return issues
