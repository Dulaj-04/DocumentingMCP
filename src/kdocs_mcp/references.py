"""IEEE-style references: a personal reference library, DOI/ISBN/URL lookup and formatting."""

from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path

from .profile import config_dir

# An entry is a plain dict:
#   key, type (article|book|chapter|inproceedings|web|datasheet|manual|report|thesis|standard|lecture),
#   authors [list of "First Last" or "Last, First"], title, journal, booktitle, publisher, address,
#   edition, volume, number, pages, year, month, doi, url, accessed (YYYY-MM-DD), organization, note

Segment = tuple[str, bool]  # (text, italic)
_MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]


# --------------------------------------------------------------------------- library


def _lib_path() -> Path:
    return config_dir() / "references.json"


def load_library() -> dict[str, dict]:
    p = _lib_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def save_library(lib: dict[str, dict]) -> None:
    p = _lib_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lib, indent=2, ensure_ascii=False), encoding="utf-8")


def make_key(entry: dict, existing: set[str]) -> str:
    first = (entry.get("authors") or [entry.get("organization") or "ref"])[0]
    last = first.split(",")[0] if "," in first else first.split()[-1]
    base = re.sub(r"[^a-z0-9]", "", last.lower()) + str(entry.get("year", ""))
    base = base or "ref"
    key, n = base, 1
    while key in existing:
        key = f"{base}{chr(ord('a') + n)}"
        n += 1
    return key


# --------------------------------------------------------------------------- lookup


def lookup(identifier: str, timeout: float = 15.0, transport=None) -> dict:
    """Build an entry from a DOI, ISBN or web URL using Crossref / Open Library / the page itself."""
    import httpx

    ident = identifier.strip()
    doi = re.search(r"(10\.\d{4,9}/[^\s\"<>]+)", ident)
    isbn = re.sub(r"[^0-9Xx]", "", ident) if re.fullmatch(r"(?:ISBN[: ]*)?[0-9Xx\- ]{10,17}", ident, re.I) else ""
    headers = {"User-Agent": "KDocs MCP/0.2 (student report generator)"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers, transport=transport) as client:
        if doi:
            r = client.get(f"https://api.crossref.org/works/{doi.group(1)}")
            r.raise_for_status()
            m = r.json()["message"]
            kind = {"journal-article": "article", "proceedings-article": "inproceedings", "book": "book",
                    "book-chapter": "chapter", "report": "report", "standard": "standard"}.get(m.get("type", ""), "article")
            parts = (m.get("issued") or m.get("published-print") or m.get("published-online") or {}).get("date-parts", [[None]])[0]
            return _compact({
                "type": kind,
                "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in m.get("author", [])],
                "title": html.unescape((m.get("title") or [""])[0]),
                "journal": (m.get("container-title") or [""])[0] if kind == "article" else None,
                "booktitle": (m.get("container-title") or [""])[0] if kind in ("inproceedings", "chapter") else None,
                "publisher": m.get("publisher") if kind in ("book", "chapter", "report", "standard") else None,
                "volume": m.get("volume"),
                "number": m.get("issue"),
                "pages": (m.get("page") or "").replace("-", "–") or None,
                "year": parts[0] if parts else None,
                "month": parts[1] if len(parts) > 1 else None,
                "doi": m.get("DOI"),
            })
        if isbn:
            r = client.get("https://openlibrary.org/api/books", params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"})
            r.raise_for_status()
            data = r.json().get(f"ISBN:{isbn}")
            if not data:
                raise ValueError(f"No book found for ISBN {isbn}")
            year = re.search(r"\d{4}", data.get("publish_date", ""))
            places = data.get("publish_places") or []
            return _compact({
                "type": "book",
                "authors": [a["name"] for a in data.get("authors", [])],
                "title": data.get("title", "") + (f": {data['subtitle']}" if data.get("subtitle") else ""),
                "publisher": (data.get("publishers") or [{}])[0].get("name"),
                "address": places[0]["name"] if places else None,
                "year": int(year.group(0)) if year else None,
                "isbn": isbn,
            })
        if re.match(r"https?://", ident):
            r = client.get(ident)
            r.raise_for_status()
            page = r.text[:200_000]

            def meta(name: str) -> str | None:
                m = re.search(rf'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]+content=["\']([^"\']+)', page, re.I) or \
                    re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{name}["\']', page, re.I)
                return html.unescape(m.group(1)).strip() if m else None

            title = meta("og:title") or meta("citation_title")
            if not title:
                t = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
                title = html.unescape(t.group(1)).strip() if t else ident
            authors = re.findall(r'<meta[^>]+name=["\']citation_author["\'][^>]+content=["\']([^"\']+)', page, re.I)
            if not authors and meta("author"):
                authors = [meta("author")]
            year = meta("citation_publication_date") or meta("article:published_time") or ""
            y = re.search(r"\d{4}", year)
            return _compact({
                "type": "web",
                "authors": authors,
                "organization": meta("og:site_name"),
                "title": " ".join(title.split()),
                "year": int(y.group(0)) if y else None,
                "url": str(r.url),
                "accessed": dt.date.today().isoformat(),
            })
    raise ValueError("Give a DOI (10.xxxx/...), an ISBN, or a web URL (https://...).")


def _compact(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None, "", [])}


# --------------------------------------------------------------------------- IEEE formatting


_SUFFIX = re.compile(r"^(?:Jr\.?|Sr\.?|II|III|IV|V)$")


def _initials(name: str) -> str:
    name = name.strip()
    if not name:
        return ""
    suffix = ""
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        if len(parts) >= 3 and _SUFFIX.match(parts[-1]):
            suffix = parts.pop()
        last, first = parts[0], " ".join(parts[1:])
    else:
        parts = name.split()
        if len(parts) > 2 and _SUFFIX.match(parts[-1]):
            suffix = parts.pop()
        if len(parts) == 1:
            return (parts[0] + (" " + suffix if suffix else "")).strip()
        last, first = parts[-1], " ".join(parts[:-1])
    if suffix:
        last = f"{last} {suffix}"
    inits = []
    for part in re.split(r"\s+", first):
        if not part:
            continue
        hy = [f"{p[0]}." for p in part.split("-") if p]
        inits.append("-".join(hy))
    return (" ".join(inits) + " " + last).strip()


def format_authors(authors: list[str]) -> str:
    names = [_initials(a) for a in authors if a and a.strip()]
    if not names:
        return ""
    if len(names) > 6:
        return names[0] + " et al."
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _date(e: dict) -> str:
    y = e.get("year")
    m = e.get("month")
    if y and m:
        try:
            return f"{_MONTHS[int(m) - 1]} {y}"
        except (ValueError, IndexError):
            return f"{m} {y}"
    return str(y) if y else ""


def _accessed(e: dict) -> str:
    a = e.get("accessed")
    if not a:
        return ""
    try:
        d = dt.date.fromisoformat(str(a))
        return f" (accessed {_MONTHS[d.month - 1]} {d.day}, {d.year})"
    except ValueError:
        return f" (accessed {a})"


def format_ieee(e: dict) -> list[Segment]:
    kind = (e.get("type") or "article").lower()
    who = format_authors(e.get("authors") or []) or e.get("organization", "")
    title = (e.get("title") or "").rstrip(".")
    date = _date(e)
    out: list[Segment] = []

    def add(text: str, italic: bool = False) -> None:
        if text:
            out.append((text, italic))

    lead = f"{who}, " if who else ""
    if kind == "book":
        add(lead)
        add(title, True)
        ed = e.get("edition")
        if ed:
            ed = str(ed)
            if ed.isdigit():
                n = int(ed)
                suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
                ed = f"{n}{suffix}"
            add(f", {ed} ed")
        place = ", ".join(x for x in (e.get("address"), e.get("publisher")) if x)
        add(". " + (f"{e['address']}: {e['publisher']}" if e.get("address") and e.get("publisher") else place) + (f", {date}." if date else "."))
    elif kind in ("chapter", "inproceedings"):
        add(f'{lead}"{title}," in ')
        add(e.get("booktitle") or "Proceedings", True)
        tail = [x for x in (e.get("address"), e.get("publisher"), date) if x]
        if e.get("pages"):
            tail.append(f"pp. {e['pages']}")
        add(", " + ", ".join(tail) + "." if tail else ".")
    elif kind == "article":
        add(f'{lead}"{title}," ')
        add(e.get("journal", ""), True)
        tail = []
        if e.get("volume"):
            tail.append(f"vol. {e['volume']}")
        if e.get("number"):
            tail.append(f"no. {e['number']}")
        if e.get("pages"):
            tail.append(f"pp. {e['pages']}")
        if date:
            tail.append(date)
        add((", " + ", ".join(tail)) if tail else "")
        add(".")
    elif kind in ("preprint", "arxiv"):
        add(f'{lead}"{title}," ')
        ident = e.get("eprint") or e.get("number") or ""
        archive = e.get("publisher") or ("arXiv" if "arxiv" in str(ident).lower() or kind == "arxiv" else "")
        where = f"{archive} preprint {ident}".replace("preprint arXiv:", "preprint arXiv:").strip() if (archive or ident) else "Preprint"
        add(where + (f", {date}." if date else "."))
    elif kind in ("web", "online", "lecture", "datasheet", "manual", "report", "thesis", "standard"):
        add(f'{lead}"{title},"')
        descr = {
            "datasheet": " Datasheet",
            "manual": " User manual",
            "lecture": " Lecture notes",
            "thesis": " Thesis",
            "report": " Tech. Rep.",
            "standard": " Standard",
        }.get(kind, "")
        if descr:
            add(descr + ",")
        org = e.get("organization") if who != e.get("organization") else None
        if org:
            add(f" {org},")
        if e.get("publisher") and kind != "web":
            add(f" {e['publisher']},")
        if date:
            add(f" {date}.")
        else:
            last = out[-1][0]
            last = last[:-2] + '."' if last.endswith(',"') else last.rstrip(",") + "."
            out[-1] = (last, out[-1][1])
        if e.get("url"):
            add(f" [Online]. Available: {e['url']}{_accessed(e)}")
    else:
        add(f'{lead}"{title}," {date}.')
    if e.get("doi"):
        txt = out[-1][0].rstrip()
        if not txt.endswith("."):
            txt += "."
        out[-1] = (txt, out[-1][1])
        add(f" doi: {e['doi']}.")
    return out


def to_plain(segments: list[Segment]) -> str:
    return "".join(t for t, _ in segments)
