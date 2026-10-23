"""The student's image library: a folder in Downloads where screenshots and photos are collected,
given sensible names, and found again by the builder.

Originals are never moved or deleted: importing copies, renaming only touches files inside the library.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from PIL import Image as PILImage

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf"}
LIBRARY_NAME = "KDocs Images"


def library_dir() -> Path:
    """The student's image folder: KDOCS_MCP_IMAGES, else the folder saved in the profile (image_dir),
    else Downloads/KDocs Images."""
    env = os.environ.get("KDOCS_MCP_IMAGES")
    if env:
        return Path(env).expanduser()
    from .profile import load_profile

    saved = load_profile().image_dir
    if saved:
        return Path(saved).expanduser()
    downloads = Path.home() / "Downloads"
    return (downloads if downloads.is_dir() else Path.home()) / LIBRARY_NAME


def slug(name: str) -> str:
    """A tidy file name: lower case, words joined by hyphens, no characters Windows dislikes."""
    name = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().lower()).strip("-")
    return name[:80] or "image"


def _unique(folder: Path, stem: str, ext: str) -> Path:
    cand = folder / f"{stem}{ext}"
    n = 2
    while cand.exists():
        cand = folder / f"{stem}-{n}{ext}"
        n += 1
    return cand


def _folder(project: str) -> Path:
    base = library_dir()
    return base / slug(project) if project else base


def info(path: Path) -> dict:
    """Facts the AI needs to choose a placement: size, shape and file weight."""
    out = {"file": path.name, "kb": round(path.stat().st_size / 1024)}
    try:
        with PILImage.open(path) as im:
            w, h = im.size
        out.update(width_px=w, height_px=h, shape="landscape" if w > h * 1.15 else "portrait" if h > w * 1.15 else "square")
        if min(w, h) < 400:
            out["note"] = "small image: may look blurry if enlarged"
    except Exception:
        out["note"] = "could not read this image"
    return out


# --------------------------------------------------------------------------- descriptions (index.json)


def _index_path() -> Path:
    return library_dir() / "index.json"


def load_index() -> dict:
    try:
        return json.loads(_index_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_index(index: dict) -> None:
    _index_path().parent.mkdir(parents=True, exist_ok=True)
    _index_path().write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")


def _key(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(library_dir().resolve())).replace("\\", "/")
    except ValueError:
        return path.name


def describe(path: str, description: str, tags: list[str] | None = None) -> dict:
    """Store what an image shows (one plain sentence) and optional topic tags. The sentence is used as the
    text under the image, and to decide where the image belongs in a report."""
    f = find(path)
    if f is None:
        return {"error": f"No such image in the library: {path}"}
    index = load_index()
    entry = index.setdefault(_key(f), {})
    entry["description"] = description.strip()
    if tags is not None:
        entry["tags"] = [x.strip().lower() for x in tags if x.strip()]
    _save_index(index)
    return {"path": str(f), **entry}


def import_images(sources: list[str], names: list[str] | None = None, project: str = "",
                  descriptions: list[str] | None = None) -> dict:
    """Copy images (files, or every image in a folder) into the library, optionally giving them new names."""
    dest = _folder(project)
    dest.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    problems: list[str] = []
    for s in sources:
        p = Path(s).expanduser()
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXT)
        elif p.is_file() and p.suffix.lower() in IMAGE_EXT:
            files.append(p)
        else:
            problems.append(f"Not an image or folder: {s}")
    if names and len(names) != len(files):
        problems.append(f"{len(names)} names were given for {len(files)} images; names were ignored.")
        names = None
    if descriptions and len(descriptions) != len(files):
        problems.append(f"{len(descriptions)} descriptions were given for {len(files)} images; they were ignored.")
        descriptions = None
    imported = []
    for i, f in enumerate(files):
        stem = slug(names[i]) if names else slug(f.stem)
        target = _unique(dest, stem, f.suffix.lower())
        shutil.copy2(f, target)
        if descriptions and descriptions[i].strip():
            describe(str(target), descriptions[i])
        imported.append({"from": str(f), "path": str(target), **info(target)})
    return {"library": str(dest), "imported": imported, "problems": problems}


def list_library(project: str = "") -> dict:
    root = _folder(project)
    if not root.is_dir():
        return {"library": str(root), "images": [], "note": "Nothing imported yet. Use import_images."}
    index = load_index()
    images = []
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.suffix.lower() in IMAGE_EXT:
            entry = index.get(_key(f), {})
            images.append({"path": _key(f), **info(f), **sizing_for(f), "description": entry.get("description", ""),
                           "tags": entry.get("tags", [])})
        if len(images) >= 300:
            break
    return {"library": str(root), "images": images}


def rename(path: str, new_name: str) -> dict:
    """Rename an image inside the library (never anywhere else). The extension is kept."""
    src = find(path)
    if src is None:
        return {"error": f"No such image in the library: {path}"}
    target = _unique(src.parent, slug(Path(new_name).stem), src.suffix.lower())
    if target.name == src.name:
        return {"path": str(src), "renamed": False}
    index = load_index()
    old_key = _key(src)
    src.rename(target)
    if old_key in index:
        index[_key(target)] = index.pop(old_key)
        _save_index(index)
    return {"old": str(src), "path": str(target), "renamed": True}


def find(ref: str) -> Path | None:
    """Locate an image in the library by relative path or bare file name."""
    p = Path(ref).expanduser()
    lib = library_dir()
    if p.is_absolute():
        try:
            p.resolve().relative_to(lib.resolve())
        except ValueError:
            return None
        return p if p.is_file() else None
    direct = lib / p
    if direct.is_file():
        return direct
    if lib.is_dir():
        hits = [f for f in lib.rglob(p.name) if f.is_file()]
        if len(hits) == 1:
            return hits[0]
    return None


# --------------------------------------------------------------------------- deciding where images belong

_STOP = set("""a an the of to in on at for and or with by from as is are was were be been this that these those it its
into than then so such not no we our i my you your can could would should will shall has have had do does did
figure fig shows show shown showing image photo picture screenshot used using use also which when where what""".split())


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower().replace("_", " ").replace("-", " "))
    out = set()
    for w in words:
        if w in _STOP or len(w) < 3:
            continue
        for suf in ("ing", "es", "s", "ed"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def _paragraphs(lines: list[str], start: int, end: int) -> list[tuple[int, str]]:
    """(line number after the paragraph, text) for each plain paragraph between two lines."""
    out, buf, first = [], [], None
    in_fence = False
    for i in range(start, end):
        ln = lines[i]
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            buf, first = [], None
            continue
        if in_fence:
            continue
        if ln.strip() and not ln.lstrip().startswith(("#", "|", "![", "$$", "<!--")):
            first = i if first is None else first
            buf.append(ln.strip())
        else:
            if buf:
                out.append((i, " ".join(buf)))
            buf, first = [], None
    if buf:
        out.append((end, " ".join(buf)))
    return out


def suggest_placement(body_markdown: str, project: str = "", max_per_section: int = 3) -> dict:
    """Match library images to the report's sections by what each image shows and what each section says.

    Also proposes which images belong together as a row, a sensible order within each section, where an
    image already used elsewhere would also fit, and whether the report is getting crowded with images.
    The result is advice, not a decision: the AI must still check it and the student confirms."""
    from . import image_plan
    from . import project as proj

    lib_images = list_library(project).get("images", [])
    used = set(re.findall(r"!\[[^\]]*\]\(([^)\s]+)", body_markdown))
    used_names = {Path(u).name for u in used}
    lines = body_markdown.splitlines()
    heads = proj.sections(body_markdown)
    sec_info = []
    for k, h in enumerate(heads):
        stop = heads[k + 1].start if k + 1 < len(heads) else len(lines)
        paras = _paragraphs(lines, h.start + 1, stop)  # a section's own text, up to the next heading
        sec_info.append((h, paras))
    img_tokens = {}
    undescribed = []
    for im in lib_images:
        text = " ".join([Path(im["file"]).stem, im.get("description", ""), " ".join(im.get("tags", []))])
        img_tokens[im["path"]] = _tokens(text)
        if not im.get("description"):
            undescribed.append(im["path"])
    suggestions = []
    matched: set[str] = set()
    reuse = []
    for h, paras in sec_info:
        title_t = _tokens(h.title)
        body_t = _tokens(" ".join(t for _, t in paras))
        cands, also = [], []
        for im in lib_images:
            toks = img_tokens[im["path"]]
            score = 3 * len(toks & title_t) + len(toks & body_t)
            if score < 2:
                continue
            ranked = [(len(toks & _tokens(p_[1])), n, p_) for n, p_ in enumerate(paras)]
            top = max(ranked, default=None)
            hit = top is not None and top[0] > 0
            entry = {"image": im["path"], "score": score, "description": im.get("description", ""), "shape": im.get("shape", ""),
                     "after_text": top[2][1][:70] if hit else "", "para_index": top[1] if hit else None}
            if im["file"] in used_names:
                if score >= 4:
                    also.append({k: entry[k] for k in ("image", "score", "description", "after_text")})
            else:
                cands.append(entry)
        cands.sort(key=lambda c: -c["score"])
        cands = cands[:max_per_section]
        if also:
            reuse.append({"section": h.title, "images_already_used_elsewhere": also[:2],
                          "note": "the same image can be used again here if it supports this section too (ask the student)"})
        if cands:
            matched.update(c["image"] for c in cands)
            ordered, basis = image_plan.order_candidates(cands)
            groups = image_plan.group_candidates(ordered)
            suggestions.append({"section": h.title, "candidates": ordered, "order_basis": basis, "groups": groups})
    return {
        "suggestions": suggestions,
        "could_also_fit": reuse,
        "not_matched_anywhere": [im["path"] for im in lib_images if im["path"] not in matched and im["file"] not in used_names],
        "already_in_report": sorted(used_names & {im["file"] for im in lib_images}),
        "needs_description": undescribed,
        "crowding_in_current_report": image_plan.crowding(body_markdown),
        "how_to_use": "Check each match yourself. Show the student the proposed groups, order, sizes and positions and "
        "get their agreement, then insert with place_images (preview first, then confirmed=true).",
    }


# --------------------------------------------------------------------------- sizing

MIN_DPI = 110  # below this a picture looks soft when printed
MAX_H_LANDSCAPE = 5.0  # inches; keeps an image from taking over a page
MAX_H_PORTRAIT = 4.6
MAX_H_SQUARE = 4.2
SIZE_WORDS = {"small": 0.35, "medium": 0.6, "large": 0.8, "full": 1.0}  # share of the figure width


def fit_size(w_px: int, h_px: int, ext: str, max_w: float, share: float | None = None) -> tuple[float, list[str]]:
    """Width in inches for one image placed on its own, and notes about its quality.

    Too small and detail is lost; too large and the layout breaks. So:
    - screenshots, diagrams and graphs (png, gif, bmp) are shown wide enough to read their text;
    - photos (jpeg) are shown smaller, and portrait or square ones are limited by height;
    - nothing is enlarged past MIN_DPI, since that only makes it blurry;
    - nothing is taller than about half a page.
    share: a fraction of max_w asked for by the author; it is still held inside the limits.
    """
    notes: list[str] = []
    aspect = w_px / h_px
    photo = ext.lower() in (".jpg", ".jpeg", ".tif", ".tiff")
    max_h = MAX_H_PORTRAIT if aspect < 0.95 else MAX_H_SQUARE if aspect < 1.2 else MAX_H_LANDSCAPE
    if share is not None:
        width = max_w * share
    elif photo:
        width = max_w * (0.62 if aspect >= 1.15 else 0.5)
    else:
        width = max_w * (0.95 if aspect >= 1.2 else 0.75 if aspect >= 0.95 else 0.5)
        if w_px < 700:
            width = min(width, w_px / 100)  # small screenshot: natural size, not blown up
    # a screenshot or photo that is too small to read gets a sensible floor
    floor = (3.2 if photo else 4.2) if aspect >= 0.95 else 2.6
    width = max(width, min(floor, max_w))
    width = min(width, max_w, max_h * aspect)
    sharp = w_px / MIN_DPI
    if width > sharp:
        if sharp >= floor * 0.75:
            width = sharp
        else:
            width = max(sharp, floor * 0.75)
            notes.append(
                f"Low resolution ({w_px}x{h_px} px): at {width:.1f} in wide it would be about {w_px / width:.0f} dpi, "
                "so it will look soft and fine detail will be lost. Ask for a larger original or a screenshot at full size."
            )
    if min(w_px, h_px) < 250:
        notes.append("Very small image: there is little detail to show, so it is kept at a modest size.")
        width = min(width, max(w_px / 150, 1.2))
    return round(width, 2), notes


def sizing_for(path: Path, max_w: float = 6.7) -> dict:
    """What the report would do with this image, for list_images / place_image."""
    try:
        with PILImage.open(path) as im:
            w, h = im.size
    except Exception:
        return {}
    width, notes = fit_size(w, h, path.suffix, max_w)
    return {"shown_width_in": width, "shown_height_in": round(width * h / w, 2), "sizing_notes": notes}
