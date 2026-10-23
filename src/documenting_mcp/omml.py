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
            results[current] = copy.deepcopy(omath)
    return results
