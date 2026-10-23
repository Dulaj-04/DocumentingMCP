"""Editable document sources.

Every generated .docx gets a sidecar `<name>.docmcp.json` holding the Markdown body and settings. Edits
are applied to that source and the document is rebuilt, so formatting stays exactly in the master
style no matter how many times a section is changed.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

SIDECAR_SUFFIX = ".docmcp.json"


@dataclass
class DocSource:
    template: str
    title: str
    body_markdown: str
    module: str = ""
    submission_date: str = ""
    assets_dir: str = ""
    filename: str = ""
    name: str = ""
    reg_no: str = ""
    intake: str = ""
    options: dict = field(default_factory=dict)
    references: list[dict] = field(default_factory=list)


def sidecar_for(docx_path: str | Path) -> Path:
    p = Path(docx_path).expanduser()
    if p.name.endswith(SIDECAR_SUFFIX):
        return p
    return p.with_name(p.stem + SIDECAR_SUFFIX)


def save_source(docx_path: Path, src: DocSource) -> Path:
    path = sidecar_for(docx_path)
    path.write_text(json.dumps(asdict(src), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_source(docx_path: str | Path) -> DocSource:
    path = sidecar_for(docx_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"No editable source found for {Path(docx_path).name}. Only documents created by DocumentingMCP "
            f"can be edited section by section (expected {path.name} next to the .docx)."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    known = DocSource.__dataclass_fields__
    return DocSource(**{k: v for k, v in data.items() if k in known})


# --------------------------------------------------------------------------- Markdown sections

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Section:
    index: int  # 1-based position among all headings
    level: int
    title: str
    start: int  # line index of the heading
    end: int  # exclusive line index where the section (with its sub-sections) ends
    question: int | None = None  # 1-based number among level-1 headings (questions in assignments)


def _norm(text: str) -> str:
    text = re.sub(r"\{[^}]*\}\s*$", "", text)  # drop {#id} attributes
    text = re.sub(r"^\s*(?:Q(?:uestion)?\s*)?\d+\s*[.):]\s*", "", text, flags=re.I)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def sections(md: str) -> list[Section]:
    lines = md.splitlines()
    heads: list[tuple[int, int, str]] = []
    in_fence = False
    for i, ln in enumerate(lines):
        if _FENCE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING.match(ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    out: list[Section] = []
    q = 0
    for k, (i, level, title) in enumerate(heads):
        end = len(lines)
        for j, lvl, _ in heads[k + 1 :]:
            if lvl <= level:
                end = j
                break
        question = None
        if level == 1 and _norm(title) not in ("references", "bibliography", "reference list", "appendix"):
            q += 1
            question = q
        out.append(Section(k + 1, level, title, i, end, question))
    return out


def outline(md: str) -> list[dict]:
    lines = md.splitlines()
    return [
        {
            "index": s.index,
            "level": s.level,
            "title": s.title,
            "question": s.question,
            "words": len(" ".join(lines[s.start + 1 : s.end]).split()),
        }
        for s in sections(md)
    ]


def find_section(md: str, target: str | int) -> Section:
    secs = sections(md)
    if not secs:
        raise ValueError("The document has no headings.")
    t = str(target).strip()
    m = re.fullmatch(r"(?:q(?:uestion)?\s*)?(\d+)", t, re.I)
    if m and re.match(r"q", t, re.I):
        n = int(m.group(1))
        for s in secs:
            if s.question == n:
                return s
        raise ValueError(f"There is no question {n}.")
    if m:
        n = int(m.group(1))
        if 1 <= n <= len(secs):
            return secs[n - 1]
    want = _norm(t)
    exact = [s for s in secs if _norm(s.title) == want]
    if exact:
        return exact[0]
    partial = [s for s in secs if want and want in _norm(s.title)]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError(f"'{target}' matches several headings: " + "; ".join(s.title for s in partial))
    raise ValueError(f"No heading matches '{target}'. Headings: " + "; ".join(s.title for s in secs))


def replace_section(md: str, target: str | int, new_markdown: str, keep_heading: bool = True) -> str:
    lines = md.splitlines()
    s = find_section(md, target)
    new = new_markdown.strip("\n").splitlines()
    if keep_heading and not (new and _HEADING.match(new[0])):
        new = [lines[s.start], ""] + new
    return "\n".join(lines[: s.start] + new + [""] + lines[s.end :]).rstrip() + "\n"


def insert_section(md: str, new_markdown: str, after: str | int | None = None, before: str | int | None = None) -> str:
    lines = md.splitlines()
    new = new_markdown.strip("\n").splitlines()
    if before is not None:
        at = find_section(md, before).start
    elif after is not None:
        at = find_section(md, after).end
    else:
        at = len(lines)
        refs = [s for s in sections(md) if s.level == 1 and _norm(s.title) in ("references", "bibliography")]
        if refs:  # new questions go before the reference list
            at = refs[0].start
    return "\n".join(lines[:at] + ([""] if at and lines[at - 1].strip() else []) + new + [""] + lines[at:]).rstrip() + "\n"


def delete_section(md: str, target: str | int) -> str:
    lines = md.splitlines()
    s = find_section(md, target)
    return "\n".join(lines[: s.start] + lines[s.end :]).rstrip() + "\n"


def replace_text(md: str, find: str, replace: str, count: int = 0) -> tuple[str, int]:
    n = md.count(find)
    if n == 0:
        return md, 0
    return (md.replace(find, replace) if count <= 0 else md.replace(find, replace, count)), (n if count <= 0 else min(n, count))
