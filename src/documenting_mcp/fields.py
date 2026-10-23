"""Word fields (SEQ, REF, PAGE, TOC) and bookmarks, written with cached results so documents read
correctly before Word refreshes them."""

from __future__ import annotations

import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

_bm_id = [1000]


def _run(p, text: str | None = None, *, bold: bool = False, italic: bool = False, size_pt: float | None = None):
    r = OxmlElement("w:r")
    if bold or italic or size_pt:
        rpr = OxmlElement("w:rPr")
        if bold:
            rpr.append(OxmlElement("w:b"))
        if italic:
            rpr.append(OxmlElement("w:i"))
        if size_pt:
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), str(int(size_pt * 2)))
            rpr.append(sz)
        r.append(rpr)
    if text is not None:
        t = OxmlElement("w:t")
        t.text = text
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        r.append(t)
    p._p.append(r)
    return r


def add_field(p, instr: str, cached: str, *, bold: bool = False, italic: bool = False, size_pt: float | None = None) -> None:
    """Append a complex field { instr } showing `cached` until Word updates it."""
    def fld(kind: str):
        r = _run(p, bold=bold, italic=italic, size_pt=size_pt)
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), kind)
        r.append(fc)

    fld("begin")
    r = _run(p, bold=bold, italic=italic, size_pt=size_pt)
    it = OxmlElement("w:instrText")
    it.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    it.text = f" {instr.strip()} "
    r.append(it)
    fld("separate")
    _run(p, cached, bold=bold, italic=italic, size_pt=size_pt)
    fld("end")


def bookmark_name(label: str) -> str:
    # Hidden bookmarks start with "_"; Word limits names to 40 characters.
    return ("_Ref_" + re.sub(r"[^A-Za-z0-9_]", "_", label))[:40]


def bookmark_start(p, name: str) -> str:
    _bm_id[0] += 1
    bid = str(_bm_id[0])
    el = OxmlElement("w:bookmarkStart")
    el.set(qn("w:id"), bid)
    el.set(qn("w:name"), name)
    p._p.append(el)
    return bid


def bookmark_end(p, bid: str) -> None:
    el = OxmlElement("w:bookmarkEnd")
    el.set(qn("w:id"), bid)
    p._p.append(el)


def internal_link(p, anchor: str, text: str) -> None:
    """Clickable link to a bookmark (used for [n] citations -> reference list)."""
    h = OxmlElement("w:hyperlink")
    h.set(qn("w:anchor"), anchor)
    h.set(qn("w:history"), "1")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    r.append(t)
    h.append(r)
    p._p.append(h)


def set_update_fields_on_open(doc) -> None:
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is not None:
        return
    el = OxmlElement("w:updateFields")
    el.set(qn("w:val"), "true")
    anchor = None
    for tag in ("w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr", "w:compat", "w:docVars", "w:rsids"):
        anchor = settings.find(qn(tag))
        if anchor is not None:
            break
    if anchor is not None:
        anchor.addprevious(el)
    else:
        settings.append(el)
