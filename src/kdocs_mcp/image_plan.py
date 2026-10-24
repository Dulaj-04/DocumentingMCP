"""Planning several images at once: which belong together, what order, whether the page gets crowded, where
page breaks are likely to fall, and the markdown edit that puts a whole plan into the report.

Everything here works on the report's Markdown and the image library, so it can be previewed before anything
is changed. The student confirms the order, sizes and positions first."""

from __future__ import annotations

import math
import re
from pathlib import Path

from . import images as lib
from . import project as proj

CONTRAST = {"before", "after", "input", "output", "with", "without", "old", "new", "left", "right", "front",
            "back", "top", "bottom", "initial", "final", "start", "end", "low", "high", "open", "closed"}
IMAGE_BLOCK = re.compile(r"^\s*!\[")
USABLE_H = 9.6  # inches of text height on a page (11 in less the margins)
FIGURE_W = 6.7


# --------------------------------------------------------------------------- order and grouping


def natural_key(name: str) -> list:
    """Sort 'scope-2' before 'scope-10': numbers compare as numbers."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", Path(name).stem.lower())]


def _signature(text: str) -> str:
    """Names or descriptions that differ only in a number or a contrast word share one signature."""
    t = re.sub(r"\d+(?:\.\d+)?", "#", text.lower().replace("_", " ").replace("-", " "))
    words = [("~" if w in CONTRAST else w) for w in re.findall(r"[a-z#~]+", t)]
    return " ".join(words)


def group_candidates(cands: list[dict]) -> list[dict]:
    """Images that look like a set (same thing at different settings, before/after, input/output)."""
    buckets: dict[str, list[dict]] = {}
    for c in cands:
        stem = Path(c["image"]).stem
        buckets.setdefault("n:" + _signature(stem), []).append(c)
    groups = []
    seen: set[str] = set()
    for key, items in buckets.items():
        if len(items) >= 2 and len(key) > 4:
            reason = "the file names differ only by a number or a before/after-type word"
            groups.append((items, reason))
            seen.update(i["image"] for i in items)
    desc_buckets: dict[str, list[dict]] = {}
    for c in cands:
        if c["image"] in seen or not c.get("description"):
            continue
        desc_buckets.setdefault(_signature(c["description"]), []).append(c)
    for sig, items in desc_buckets.items():
        if len(items) >= 2 and len(sig.split()) >= 3:
            groups.append((items, "the descriptions are the same apart from a value or a before/after-type word"))
    out = []
    for items, reason in groups:
        items = sorted(items, key=lambda c: natural_key(c["image"]))
        for i in range(0, len(items), 3):  # a row holds at most three
            chunk = items[i : i + 3]
            if len(chunk) >= 2:
                out.append({"images": [c["image"] for c in chunk], "reason": reason,
                            "suggest": "put these side by side in one row, labelled (a), (b), (c)" if len(chunk) <= 3 else ""})
    return out


def order_candidates(cands: list[dict]) -> tuple[list[dict], str]:
    """Order images within a section: as the text discusses them; ties by numbered file name."""
    if len(cands) < 2:
        return cands, ""
    by_text = any(c.get("para_index") is not None for c in cands)
    ordered = sorted(cands, key=lambda c: (c.get("para_index") if c.get("para_index") is not None else 10**6, natural_key(c["image"])))
    positions = [c.get("para_index") for c in ordered]
    if by_text and len({p for p in positions if p is not None}) == len([p for p in positions if p is not None]) and None not in positions:
        basis = "the order in which the text discusses them (confirm with the student)"
    elif any(re.search(r"\d", Path(c["image"]).stem) for c in ordered):
        basis = "numbered file names, as the text does not make the order clear (ask the student)"
    else:
        basis = "alphabetical only: the order is a guess (ask the student)"
    return ordered, basis


# --------------------------------------------------------------------------- crowding and layout


def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def _blocks(markdown: str) -> list[tuple[str, str, int]]:
    """Coarse blocks of the document: (kind, text, line). kinds: heading, para, image, list, table, code, math, visual."""
    out, buf, first = [], [], 0
    fence = None

    def flush() -> None:
        nonlocal buf
        if buf:
            out.append(("para", " ".join(buf), first))
            buf = []

    lines = markdown.splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if fence is not None:
            if s.startswith("```"):
                out.append((fence[0], "\n".join(fence[1]), fence[2]))
                fence = None
            else:
                fence[1].append(ln)
            continue
        if s.startswith("```"):
            flush()
            lang = s[3:].strip().lower().split("{")[0].strip()
            kind = "visual" if lang in ("plot", "diagram", "circuit") else "profile" if lang.lstrip(".") in ("profile", "equipment") else "code"
            fence = (kind, [], i)
            continue
        if not s:
            flush()
        elif s.startswith("#"):
            flush()
            out.append(("heading", s.lstrip("# "), i))
        elif s.startswith("!["):
            flush()
            out.append(("image", s, i))
        elif s.startswith("|"):
            flush()
            out.append(("table", s, i))
        elif s.startswith(("- ", "* ")) or re.match(r"\d+[.)]\s", s):
            flush()
            out.append(("list", s, i))
        elif s.startswith("$$"):
            flush()
            out.append(("math", s, i))
        elif s.startswith("<!--"):
            flush()
        else:
            if not buf:
                first = i
            buf.append(s)
    flush()
    return out


def _image_heights(block: str, max_w: float = FIGURE_W) -> tuple[float, bool, list[str]]:
    """Height in inches that an image line will take, whether it is a row, and sizing notes."""
    items = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)(\{[^}]*\})?", block)
    notes: list[str] = []
    heights = []
    for name, attrs in items:
        f = lib.find(name)
        if f is None:
            heights.append(3.0)
            continue
        try:
            from PIL import Image as PILImage

            with PILImage.open(f) as im:
                w_px, h_px = im.size
        except Exception:
            heights.append(3.0)
            continue
        share = None
        m = re.search(r"width=([^\s}]+)", attrs or "")
        if m:
            val = m.group(1).strip('"')
            share = lib.SIZE_WORDS.get(val.lower())
            if share is None and val.endswith("%"):
                try:
                    share = float(val[:-1]) / 100
                except ValueError:
                    share = None
        if len(items) > 1:
            cols = min(len(items), 3) if len(items) != 4 else 2
            usable = (7.5 - 0.15 * (cols - 1)) / cols - 0.22
            heights.append(min(usable * h_px / w_px, 3.4))
        else:
            w_in, n = lib.fit_size(w_px, h_px, f.suffix, max_w, share)
            notes += n
            heights.append(w_in * h_px / w_px)
    if not heights:
        return 3.0, False, notes
    rows = math.ceil(len(items) / 3) if len(items) != 4 else 2
    if len(items) > 1:
        return min(heights) * rows + 0.5 * rows, True, notes
    return heights[0] + 0.45, False, notes


def crowding(markdown: str) -> list[dict]:
    """Places where images are piled up without enough text to carry them."""
    blocks = _blocks(markdown)
    notes: list[dict] = []
    sec = ""
    since_img_words = None
    last_img = None
    sec_words = sec_imgs = 0
    sec_start = None

    def close_section() -> None:
        if sec and sec_imgs >= 2 and sec_words / max(sec_imgs, 1) < 45:
            notes.append({"where": sec, "message": f"Section '{sec}' has {sec_imgs} images but only about {sec_words} words. "
                          "Add text that explains them, or group related images side by side, or use fewer."})

    for kind, text, line in blocks:
        if kind == "heading":
            close_section()
            sec, sec_words, sec_imgs, since_img_words, last_img = text, 0, 0, None, None
            continue
        if kind == "profile":
            sec_words += _words(text)
            sec_imgs += 1
            last_img, since_img_words = text, 0
            continue
        if kind == "image":
            sec_imgs += 1
            if last_img is not None and since_img_words is not None and since_img_words < 25:
                notes.append({"where": sec, "message": f"Two images are stacked with only {since_img_words} words between them in "
                              f"'{sec}'. Put them side by side if they belong together, or add a sentence about each."})
            last_img, since_img_words = text, 0
            continue
        w = _words(text) if kind in ("para", "list") else 0
        sec_words += w
        if since_img_words is not None:
            since_img_words += w
    close_section()
    return notes


def layout_notes(markdown: str) -> list[dict]:
    """A rough estimate of where page breaks fall and where an image would leave a large gap.

    It is only an estimate (fonts and wrapping differ), so it is phrased as such. The exported PDF is the truth."""
    used = 0.0
    page = 1
    notes: list[dict] = []
    sec = ""
    prev_h = 0.0
    prev_para = False
    for kind, text, line in _blocks(markdown):
        if kind == "heading":
            sec = text
            h = 0.6
        elif kind == "para":
            h = math.ceil(len(text) / 105) * 0.2 + 0.14
        elif kind == "list":
            h = math.ceil(len(text) / 95) * 0.2 + 0.05
        elif kind == "table":
            h = 0.27
        elif kind == "code":
            h = len(text.splitlines()) * 0.17 + 0.2
        elif kind == "math":
            h = 0.6
        elif kind == "visual":
            h = 3.7
        elif kind == "profile":
            h = max(len(re.findall(r"^\s*-?\s*[^\n:]+:", text, re.M)) * 0.22, 3.2) + 0.5
        else:  # image
            h, _row, _n = _image_heights(text)
            lead = prev_h if prev_para else 0.0  # the sentence introducing the image travels with it
            if used + h > USABLE_H and used > 0.5:
                left = USABLE_H - used
                if left + lead > 1.6:
                    ratio = (left - 0.5) / (h - 0.45) if h > 0.45 else 0
                    hint = ""
                    if 0.8 <= ratio < 1.0:
                        hint = f" Making it about {int(ratio * 100)}% of its size would let it stay on that page."
                    notes.append({"where": sec, "message": f"Estimated: this image does not fit under the text on body page {page}, which "
                                  f"leaves about {left + lead:.1f} in blank at the bottom.{hint} Moving a paragraph after it, "
                                  "or shrinking it a little, avoids the gap."})
                page += 1
                used = lead
            used += h
            prev_h, prev_para = 0.0, False
            continue
        if used + h > USABLE_H:
            page += math.ceil((used + h) / USABLE_H) - 1 if h > USABLE_H else 1
            used = h if h <= USABLE_H else h % USABLE_H
        else:
            used += h
        prev_h, prev_para = (h, True) if kind == "para" and h < 1.2 else (0.0, False)
    return notes


# --------------------------------------------------------------------------- the plan itself


def _line_for(item: dict, index: dict) -> tuple[str, list[str], list[str]]:
    """The markdown line for one plan item, the files it uses, and any problems."""
    names = [item["image"]] + list(item.get("side_by_side_with") or [])
    caption, label, width = item.get("caption", ""), item.get("label", ""), item.get("width", "")
    parts, files, problems = [], [], []
    for i, name in enumerate(names):
        f = lib.find(name)
        if f is None:
            problems.append(f"No such image in the library: {name}")
            continue
        files.append(f.name)
        own = index.get(lib._key(f), {}).get("description", "")
        text = (caption if len(names) == 1 and caption else own).strip()
        if len(names) > 1:
            text = f"({chr(97 + i)}) {text}" if text else f"({chr(97 + i)})"
        bits = []
        if i == 0 and label:
            bits.append("#fig:" + re.sub(r"[^A-Za-z0-9_-]+", "-", label.strip().removeprefix("fig:")))
        if width and len(names) == 1:
            bits.append(f"width={width}")
        if i == 0 and len(names) > 1 and caption:
            bits.append('caption="' + caption.replace('"', "'") + '"')
        parts.append(f"![{text}]({f.name}){'{' + ' '.join(bits) + '}' if bits else ''}")
    return " ".join(parts), files, problems


def apply_plan(markdown: str, plan: list[dict]) -> tuple[str, list[dict], list[str]]:
    """Insert every planned image into the markdown. Returns the new markdown, a description of each placement
    (in the order they will appear) and any problems. Nothing is written anywhere."""
    index = lib.load_index()
    problems: list[str] = []
    # order: items for the same section keep the order given; an explicit `order` wins
    indexed = list(enumerate(plan))
    indexed.sort(key=lambda p: (p[1].get("order") if p[1].get("order") is not None else 10**6, p[0]))
    placed: list[dict] = []
    last_in_anchor: dict[tuple, str] = {}
    md = markdown
    for _, item in indexed:
        line, files, probs = _line_for(item, index)
        problems += probs
        if not line or probs:
            continue
        try:
            sec = proj.find_section(md, item["section"])
        except Exception:
            problems.append(f"No section matches '{item['section']}'.")
            continue
        lines = md.splitlines()
        own_end = sec.end
        for h in proj.sections(md):
            if sec.start < h.start < own_end:
                own_end = h.start
                break
        anchor = (item["section"], (item.get("after_text") or "").lower().strip())
        at = own_end
        if anchor in last_in_anchor and last_in_anchor[anchor] in lines:
            at = lines.index(last_in_anchor[anchor]) + 1  # after the image placed just before it
        elif anchor[1]:
            hit = next((i for i in range(sec.start + 1, own_end) if anchor[1] in lines[i].lower()), None)
            if hit is None:
                problems.append(f"Could not find '{item['after_text']}' in section '{sec.title}'.")
                continue
            at = hit + 1
            while at < own_end and lines[at].strip():
                at += 1
        while at > sec.start + 1 and not lines[at - 1].strip():
            at -= 1
        lines[at:at] = ["", line, ""]
        md = "\n".join(lines) + ("\n" if markdown.endswith("\n") else "")
        last_in_anchor[anchor] = line
        placed.append({"section": sec.title, "images": files, "line": line, "after": item.get("after_text") or "(end of the section's text)",
                       "row": len(files) > 1})
    return md, placed, problems


def preview(markdown: str, plan: list[dict]) -> dict:
    """Everything the student should approve before images go in: order, position, size, page effects."""
    new_md, placed, problems = apply_plan(markdown, plan)
    index = lib.load_index()
    for p in placed:
        sizes = []
        for name in p["images"]:
            f = lib.find(name)
            info = lib.sizing_for(f) if f else {}
            sizes.append({"image": name, "shown_width_in": info.get("shown_width_in"), "shown_height_in": info.get("shown_height_in"),
                          "notes": info.get("sizing_notes", [])})
        if p["row"]:
            sizes_note = "side by side at one common height"
            for s in sizes:
                s["shown_width_in"] = s["shown_height_in"] = None
            p["size_rule"] = sizes_note
        p["sizes"] = sizes
        p["described_as"] = [index.get(lib._key(lib.find(n)), {}).get("description", "") for n in p["images"] if lib.find(n)]
    order_basis = {}
    for p in placed:
        order_basis.setdefault(p["section"], []).append(p)
    questions = []
    for sec, items in order_basis.items():
        if len(items) >= 2:
            questions.append(f"In '{sec}' the images will appear in this order: " + ", then ".join(" + ".join(i["images"]) for i in items)
                             + ". Is that the right order?")
    for p in placed:
        for s in p["sizes"]:
            if s["notes"]:
                questions.append(f"{s['image']}: {' '.join(s['notes'])} Keep it anyway, or use another image?")
        if len(p["images"]) > 1:
            questions.append(f"{' + '.join(p['images'])} will sit side by side as one figure (a), (b)... Is that what you want?")
    return {
        "placements": placed,
        "problems": problems,
        "crowding": crowding(new_md),
        "layout_estimates": layout_notes(new_md),
        "ask_the_student": questions + ["Are the positions (which paragraph each image follows) and sizes right? Anything to change?"],
        "new_markdown": new_md,
    }
