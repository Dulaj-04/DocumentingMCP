"""Live editing of a document that is open in Microsoft Word (Windows desktop Word 2013 and later,
including Microsoft 365), through Word's COM automation interface.

When the student has the document open, edits go straight into it:
- replacing / inserting / deleting a section copies only that part, fully formatted, from a freshly
  built copy, so hand edits elsewhere in the document survive;
- find-and-replace runs inside Word.
Word then refreshes fields (numbering, cross-references) and saves.

Everything that talks to Word goes through a few attributes (Documents, Paragraphs, Range, Find,
FormattedText), which keeps the logic testable with a stand-in object.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BODY_LEVEL = 10  # Word's wdOutlineLevelBodyText
WD_REPLACE_ONE = 1
WD_REPLACE_ALL = 2
WD_FIND_STOP = 0


def _norm(text: str) -> str:
    text = text.replace("\r", " ").replace("\x07", " ")
    text = re.sub(r"^\s*(?:Q(?:uestion)?\s*)?\d+(?:\.\d+)*\s*[.):]?\s+", "", text, flags=re.I)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# --------------------------------------------------------------------------- connecting to Word


def word_app(create: bool = False):
    """The running Word application (or a new one if create=True). None when Word is not available."""
    if sys.platform != "win32":
        return None
    try:
        import win32com.client
    except ImportError:
        return None
    try:
        return win32com.client.GetActiveObject("Word.Application")
    except Exception:
        if not create:
            return None
    try:
        app = win32com.client.Dispatch("Word.Application")
        app.Visible = True
        return app
    except Exception:
        return None


def _same_file(a: str, b: Path) -> bool:
    try:
        return Path(a).resolve() == b.resolve()
    except OSError:
        return str(a).lower() == str(b).lower()


def find_open_document(path: Path, app=None):
    """The Word document object if `path` is currently open in Word, else None."""
    app = app if app is not None else word_app()
    if app is None:
        return None
    try:
        for i in range(1, app.Documents.Count + 1):
            doc = app.Documents.Item(i)
            if _same_file(doc.FullName, path):
                return doc
    except Exception:
        return None
    return None


def open_document(path: Path, app=None):
    app = app if app is not None else word_app(create=True)
    if app is None:
        raise RuntimeError("Live editing needs Microsoft Word on Windows (Word 2013 or later).")
    doc = find_open_document(path, app)
    if doc is None:
        doc = app.Documents.Open(str(path.resolve()))
    app.Visible = True
    try:
        doc.Activate()
    except Exception:
        pass
    return doc


# --------------------------------------------------------------------------- locating sections


def headings(doc) -> list[tuple[int, str, int, int]]:
    """(outline level, text, start, end-of-paragraph) for every heading paragraph."""
    out = []
    for i in range(1, doc.Paragraphs.Count + 1):
        p = doc.Paragraphs.Item(i)
        level = int(p.OutlineLevel)
        if level < BODY_LEVEL:
            rng = p.Range
            out.append((level, rng.Text.strip("\r\x07 "), rng.Start, rng.End))
    return out


def section_span(doc, title: str) -> tuple[int, int] | None:
    """Character span of a section: from its heading up to the next heading of the same or higher level."""
    want = _norm(title)
    heads = headings(doc)
    idx = next((i for i, h in enumerate(heads) if _norm(h[1]) == want), None)
    if idx is None:
        idx = next((i for i, h in enumerate(heads) if want and want in _norm(h[1])), None)
    if idx is None:
        return None
    level, _t, start, _e = heads[idx]
    end = doc.Content.End - 1  # keep the final paragraph mark (it holds the section properties)
    for lvl, _t2, s2, _e2 in heads[idx + 1 :]:
        if lvl <= level:
            end = s2
            break
    return start, end


# --------------------------------------------------------------------------- live operations


def replace_section_live(doc, title: str, built_docx: Path, built_title: str | None = None) -> bool:
    """Swap one section of the open document for the same section of a freshly built copy."""
    span = section_span(doc, title)
    if span is None:
        return False
    src = doc.Application.Documents.Open(str(built_docx.resolve()), ReadOnly=True, AddToRecentFiles=False, Visible=False)
    try:
        src_span = section_span(src, built_title or title)
        if src_span is None:
            return False
        doc.Range(*span).FormattedText = src.Range(*src_span).FormattedText
    finally:
        src.Close(False)
    return True


def insert_section_live(doc, built_docx: Path, new_title: str, after: str | None, before: str | None) -> bool:
    """Insert a section taken from the built copy at the matching place in the open document."""
    if before:
        span = section_span(doc, before)
        if span is None:
            return False
        at = span[0]
    elif after:
        span = section_span(doc, after)
        if span is None:
            return False
        at = span[1]
    else:
        refs = [h for h in headings(doc) if _norm(h[1]) in ("references", "bibliography")]
        at = refs[0][2] if refs else doc.Content.End - 1
    src = doc.Application.Documents.Open(str(built_docx.resolve()), ReadOnly=True, AddToRecentFiles=False, Visible=False)
    try:
        src_span = section_span(src, new_title)
        if src_span is None:
            return False
        doc.Range(at, at).FormattedText = src.Range(*src_span).FormattedText
    finally:
        src.Close(False)
    return True


def delete_section_live(doc, title: str) -> bool:
    span = section_span(doc, title)
    if span is None:
        return False
    doc.Range(*span).Delete()
    return True


def replace_text_live(doc, find: str, replace: str, count: int = 0) -> int:
    """Find-and-replace inside Word. count=0 replaces every occurrence. Returns how many were replaced."""
    total = doc.Content.Text.count(find)
    todo = total if count <= 0 else min(count, total)
    if todo == total and total:
        rng = doc.Content
        rng.Find.ClearFormatting()
        rng.Find.Replacement.ClearFormatting()
        rng.Find.Execute(FindText=find, MatchCase=True, Forward=True, Wrap=WD_FIND_STOP, ReplaceWith=replace, Replace=WD_REPLACE_ALL)
        return total
    for _ in range(todo):  # a fresh range each time so Word searches from the top again
        rng = doc.Content
        rng.Find.ClearFormatting()
        rng.Find.Replacement.ClearFormatting()
        rng.Find.Execute(FindText=find, MatchCase=True, Forward=True, Wrap=WD_FIND_STOP, ReplaceWith=replace, Replace=WD_REPLACE_ONE)
    return todo


def finish(doc) -> None:
    """Refresh numbering and cross-references, then save so the file on disk matches what is on screen."""
    try:
        doc.Fields.Update()
        for toc in doc.TablesOfContents:
            toc.Update()
    except Exception:
        pass
    doc.Save()
