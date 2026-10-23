"""The student's image library: a folder in Downloads where screenshots and photos are collected,
given sensible names, and found again by the builder.

Originals are never moved or deleted: importing copies, renaming only touches files inside the library.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from PIL import Image as PILImage

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf"}
LIBRARY_NAME = "KDocs Images"


def library_dir() -> Path:
    """Downloads/KDocs Images (override with KDOCS_MCP_IMAGES)."""
    env = os.environ.get("KDOCS_MCP_IMAGES")
    if env:
        return Path(env).expanduser()
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


def import_images(sources: list[str], names: list[str] | None = None, project: str = "") -> dict:
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
    imported = []
    for i, f in enumerate(files):
        stem = slug(names[i]) if names else slug(f.stem)
        target = _unique(dest, stem, f.suffix.lower())
        shutil.copy2(f, target)
        imported.append({"from": str(f), "path": str(target), **info(target)})
    return {"library": str(dest), "imported": imported, "problems": problems}


def list_library(project: str = "") -> dict:
    root = _folder(project)
    if not root.is_dir():
        return {"library": str(root), "images": [], "note": "Nothing imported yet. Use import_images."}
    images = [{"path": str(f.relative_to(library_dir())).replace("\\", "/"), **info(f)}
              for f in sorted(root.rglob("*")) if f.is_file() and f.suffix.lower() in IMAGE_EXT][:300]
    return {"library": str(root), "images": images}


def rename(path: str, new_name: str) -> dict:
    """Rename an image inside the library (never anywhere else). The extension is kept."""
    src = find(path)
    if src is None:
        return {"error": f"No such image in the library: {path}"}
    target = _unique(src.parent, slug(Path(new_name).stem), src.suffix.lower())
    if target.name == src.name:
        return {"path": str(src), "renamed": False}
    src.rename(target)
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
