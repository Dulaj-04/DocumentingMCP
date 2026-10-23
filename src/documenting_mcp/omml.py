"""LaTeX -> native Word equations (OMML), using pandoc's docx writer.

All equations in a document are converted in a single pandoc run: each one is written as its own
display-math paragraph, separated by marker paragraphs, and the resulting <m:oMath> elements are
read back in order.
"""

from __future__ import annotations

import copy
import tempfile
import zipfile
from pathlib import Path

import pypandoc
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_MARK = "EQSEPMARKER"


def latex_to_omml(latex_list: list[str]) -> list[etree._Element | None]:
    """Return one <m:oMath> element per input (None where pandoc could not convert it)."""
    if not latex_list:
        return []
    parts = []
    for i, tex in enumerate(latex_list):
        tex = " ".join(tex.split())  # pandoc display math must not contain blank lines
        parts.append(f"{_MARK}{i}\n\n$${tex}$$\n")
    parts.append(f"{_MARK}{len(latex_list)}\n")
    md = "\n".join(parts)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "eq.docx"
        pypandoc.convert_text(md, "docx", format="markdown", outputfile=str(out))
        with zipfile.ZipFile(out) as z:
            root = etree.fromstring(z.read("word/document.xml"))

    results: list[etree._Element | None] = [None] * len(latex_list)
    current = None
    for p in root.iter(f"{{{W}}}p"):
        text = "".join(p.itertext()).strip()
        if text.startswith(_MARK) and text[len(_MARK):].isdigit():
            current = int(text[len(_MARK):])
            continue
        if current is None or current >= len(latex_list) or results[current] is not None:
            continue
        omath = p.find(f".//{{{M}}}oMath")
        if omath is not None:
            results[current] = _polish(copy.deepcopy(omath))
    return results


def _polish(omath: etree._Element) -> etree._Element:
    """Make the OMML look like what Word itself writes: one run per same-styled text and an explicit
    Cambria Math font on every run, so the equation keeps its font in any style context."""
    for parent in list(omath.iter()):
        prev = None
        for child in list(parent):
            if child.tag != f"{{{M}}}r":
                prev = None
                continue
            if prev is not None and _style_key(prev) == _style_key(child):
                prev_t, t = prev.find(f"{{{M}}}t"), child.find(f"{{{M}}}t")
                if prev_t is not None and t is not None and "&" not in (t.text or "") + (prev_t.text or ""):
                    prev_t.text = (prev_t.text or "") + (t.text or "")
                    parent.remove(child)
                    continue
            prev = child
    for r in omath.iter(f"{{{M}}}r"):
        t = r.find(f"{{{M}}}t")
        if t is not None and t.text and (t.text != t.text.strip()):
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        if r.find(f"{{{W}}}rPr") is None:
            wrpr = etree.Element(f"{{{W}}}rPr")
            fonts = etree.SubElement(wrpr, f"{{{W}}}rFonts")
            fonts.set(f"{{{W}}}ascii", "Cambria Math")
            fonts.set(f"{{{W}}}hAnsi", "Cambria Math")
            mrpr = r.find(f"{{{M}}}rPr")
            if mrpr is not None:
                mrpr.addnext(wrpr)
            else:
                r.insert(0, wrpr)
    return omath


def _style_key(run: etree._Element) -> bytes:
    rpr = run.find(f"{{{M}}}rPr")
    return b"" if rpr is None else etree.tostring(rpr)
