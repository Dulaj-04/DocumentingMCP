"""Regenerate the README images with KDocs MCP's own drawing tools.

    uv run python docs/make_images.py

Page renders need LibreOffice (soffice) and pdftoppm (poppler) on PATH. Every document uses a
placeholder student.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
WORK = Path(tempfile.mkdtemp())
os.environ["KDOCS_MCP_HOME"] = str(WORK / "home")

from kdocs_mcp import server  # noqa: E402
from kdocs_mcp.diagrams import render_circuit, render_flowchart  # noqa: E402
from kdocs_mcp.plots import make_plot  # noqa: E402

server.set_profile(name="A B C Student", reg_no="D/ENG/EE/25/0000", intake="42", output_dir=str(WORK / "out"))
BG = (246, 247, 249)


def font(size: int, bold: bool = False):
    for name in (("LiberationSerif-Bold.ttf" if bold else "LiberationSerif-Regular.ttf"), "DejaVuSerif.ttf"):
        for base in ("/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts"):
            p = Path(base) / name
            if p.is_file():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def card(img: Image.Image, w: int, label: str = "") -> Image.Image:
    img = img.convert("RGB")
    h = int(img.height * w / img.width)
    img = img.resize((w, h), Image.LANCZOS)
    pad, lab_h = 14, (34 if label else 0)
    c = Image.new("RGB", (w + 2 * pad, h + 2 * pad + lab_h), BG)
    sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([pad + 4, pad + 5, pad + w + 4, pad + h + 5], fill=(0, 0, 0, 60))
    c.paste(sh.filter(ImageFilter.GaussianBlur(5)), (0, 0), sh.filter(ImageFilter.GaussianBlur(5)))
    c.paste(img, (pad, pad))
    d = ImageDraw.Draw(c)
    d.rectangle([pad, pad, pad + w - 1, pad + h - 1], outline=(205, 205, 205))
    if label:
        f = font(19)
        tw = d.textlength(label, font=f)
        d.text(((c.width - tw) / 2, pad + h + 8), label, fill=(40, 40, 40), font=f)
    return c


def row(images: list[Image.Image], gap: int = 18) -> Image.Image:
    W = sum(i.width for i in images) + gap * (len(images) + 1)
    H = max(i.height for i in images) + 2 * gap
    out = Image.new("RGB", (W, H), BG)
    x = gap
    for i in images:
        out.paste(i, (x, gap + (H - 2 * gap - i.height) // 2))
        x += i.width + gap
    return out


def grid(images: list[Image.Image], cols: int) -> Image.Image:
    rows = [row(images[i : i + cols]) for i in range(0, len(images), cols)]
    W = max(r.width for r in rows)
    out = Image.new("RGB", (W, sum(r.height for r in rows)), BG)
    y = 0
    for r in rows:
        out.paste(r, ((W - r.width) // 2, y))
        y += r.height
    return out


def pages(docx: str, prefix: str) -> list[Path]:
    pdf = server.export_pdf(docx, force=True)["pdf"]
    subprocess.run(["pdftoppm", "-r", "110", "-png", pdf, str(WORK / prefix)], check=True)
    return sorted(WORK.glob(f"{prefix}-*.png"))


def save(img: Image.Image, name: str) -> None:
    img.save(OUT / name, optimize=True)
    print("wrote", OUT / name)


# --------------------------------------------------------------------------- how it works


def architecture() -> None:
    render_flowchart(
        """flowchart LR
          S([You]) -->|chat| AI[Claude / ChatGPT<br>Desktop]
          AI -->|MCP tool calls| M[KDocs MCP<br>server]
          IN[/Brief, notes,<br>data, photos/] --> M
          M --> P[Plan +<br>checklist]
          M --> B[Builder:<br>house style]
          B --> D[/Word .docx<br>+ PDF/]
        """,
        WORK / "arch.png",
    )
    save(card(Image.open(WORK / "arch.png"), 1200), "architecture.png")


def workflow() -> None:
    render_flowchart(
        """flowchart TD
          A([You describe the task]) --> B[Requirements checklist<br>+ defaults to confirm]
          B --> C[All questions asked<br>in one message]
          C --> D[Rough plan]
          D --> E{You approve<br>the plan?}
          E -- No --> D
          E -- Yes --> F[Next step: your input first<br>for ticked sections, then write]
          F --> G{Check-in:<br>happy with it?}
          G -- Change --> F
          G -- Next step --> H[Figures reviewed<br>and approved by you]
          H --> I[Pre-submission check]
          I --> J([Word + PDF])
        """,
        WORK / "flow.png",
    )
    save(card(Image.open(WORK / "flow.png"), 620), "workflow.png")


def live_editing() -> None:
    render_flowchart(
        """flowchart TD
          A([You ask for a change]) --> B{Is the document<br>open in Word?}
          B -- Yes --> C[Build a fresh copy<br>in the background]
          C --> D[Swap only the changed<br>section into Word]
          D --> E[Word renumbers fields<br>and saves]
          E --> F([Your hand edits kept])
          B -- No --> G{Edited by hand<br>since it was built?}
          G -- No --> H([Rebuild the .docx])
          G -- Yes --> I[Ask you first:<br>open in Word, or discard?]
        """,
        WORK / "live.png",
    )
    save(card(Image.open(WORK / "live.png"), 620), "live-editing.png")


# --------------------------------------------------------------------------- galleries


def plots() -> None:
    specs = {
        "Formula: 50 Hz voltage and current": {
            "x_label": "Time (ms)", "y_label": "Amplitude (V, A)",
            "series": [
                {"label": "$v(t)$", "expr": "325*sin(2*pi*50*t/1000)", "var": "t", "range": [0, 40]},
                {"label": "$i(t)$ × 100", "expr": "250*sin(2*pi*50*t/1000 - pi/6)", "var": "t", "range": [0, 40], "style": "--"},
            ],
        },
        "Log axis: RC low-pass response": {
            "x_label": "Frequency (Hz)", "y_label": "Gain (dB)", "xscale": "log",
            "series": [{"label": "$f_c$ = 1 kHz", "expr": "-10*log10(1 + (f/1000)^2)", "var": "f", "range": [10, 100000], "spacing": "log"}],
            "vlines": [{"x": 1000, "label": "−3 dB point"}],
        },
        "Bar chart: iterations to converge": {
            "type": "bar", "categories": ["Gauss–Seidel", "Fast decoupled", "Newton–Raphson"],
            "y_label": "Iterations", "series": [{"y": [38, 9, 3]}],
        },
        "Measured data with a fitted line": {
            "x_label": "Current (mA)", "y_label": "Voltage (V)",
            "series": [
                {"label": "Measured", "type": "scatter", "x": [1, 2, 3, 4, 5, 6], "y": [0.98, 2.05, 2.96, 4.1, 4.95, 6.02]},
                {"label": "$V = IR$, R = 1 kΩ", "expr": "x", "var": "x", "range": [0, 6.5], "style": "--"},
            ],
        },
    }
    imgs = []
    for i, (label, spec) in enumerate(specs.items()):
        path = WORK / f"plot{i}.png"
        make_plot({**spec, "width": 5.2}, path)
        imgs.append(card(Image.open(path), 560, label))
    save(grid(imgs, 2), "gallery-plots.png")


def circuits() -> None:
    items = {
        "RC low-pass filter": [
            {"type": "vsource", "dir": "up", "label": "$V_{in}$", "id": "vs"},
            {"type": "resistor", "dir": "right", "label": "$R$", "value": "1 kΩ"},
            {"type": "dot", "id": "n1"},
            {"type": "capacitor", "dir": "down", "label": "$C$", "value": "160 nF"},
            {"type": "line", "to": "vs.start"},
            {"type": "line", "at": "n1.center", "dir": "right", "len": 0.6, "label": "$V_{out}$", "label_loc": "right"},
            {"type": "ground", "at": "vs.start"},
        ],
        "Inverting amplifier": [
            {"type": "opamp", "id": "op"},
            {"type": "line", "at": "op.in1", "dir": "left", "len": 0.5},
            {"type": "dot", "id": "inv"},
            {"type": "resistor", "dir": "left", "label": "$R_{in}$", "value": "10 kΩ"},
            {"type": "line", "at": "inv.center", "dir": "up", "len": 0.75},
            {"type": "resistor", "dir": "right", "tox": "op.out", "label": "$R_f$", "value": "100 kΩ"},
            {"type": "line", "toy": "op.out", "dir": "down"},
            {"type": "line", "at": "op.in2", "dir": "left", "len": 0.3},
            {"type": "ground"},
            {"type": "line", "at": "op.out", "dir": "right", "len": 0.5, "label": "$V_{out}$", "label_loc": "right"},
        ],
        "LED with series resistor": [
            {"type": "battery", "dir": "up", "label": "5 V", "id": "b"},
            {"type": "switch", "dir": "right", "label": "S1"},
            {"type": "resistor", "dir": "right", "label": "$R_1$", "value": "330 Ω"},
            {"type": "led", "dir": "down", "label": "D1"},
            {"type": "line", "to": "b.start"},
            {"type": "ground", "at": "b.start"},
        ],
        "Logic: NAND followed by NOT": [
            {"type": "nand", "id": "g1", "label": "G1"},
            {"type": "line", "at": "g1.out", "dir": "right", "len": 0.4},
            {"type": "not", "label": "G2"},
        ],
    }
    imgs = []
    for i, (label, els) in enumerate(items.items()):
        path = WORK / f"circ{i}.png"
        render_circuit(els, path)
        imgs.append(card(Image.open(path), 360, label))
    save(grid(imgs, 4), "gallery-circuits.png")


def diagrams() -> None:
    flows = {
        "Flowchart (top-down)": """flowchart TD
            S([Start]) --> I[Initialise I2C]
            I --> A[Try next address]
            A --> Q{Device<br>answers?}
            Q -- No --> A
            Q -- Yes --> L[Write text to LCD]
            L --> E([End])""",
        "Feedback control loop": """flowchart LR
            R[Reference] --> E((Σ))
            E --> C[Controller] --> P[Plant] --> Y[Output]
            P --> H[Sensor]
            H -->|feedback| E""",
    }
    imgs = []
    for i, (label, text) in enumerate(flows.items()):
        path = WORK / f"diag{i}.png"
        render_flowchart(text, path)
        imgs.append(card(Image.open(path), 420 if i == 0 else 760, label))
    save(row(imgs), "gallery-diagrams.png")


# --------------------------------------------------------------------------- document features


def equations() -> None:
    res = server.create_document(
        template="assignment", title="Equations", filename="equations",
        body_markdown=(ROOT / "examples" / "equations.md").read_text(encoding="utf-8"), skip_planning=True,
    )
    page = Image.open(pages(res["docx"], "eq")[1])
    # Stop above the aligned derivation: LibreOffice (used for these renders) cannot draw Word's
    # alignment marks, although Word itself shows them correctly.
    top = page.crop((30, 55, page.width - 30, int(page.height * 0.37)))
    save(card(top, 900), "equations.png")


def tables_and_borders() -> None:
    body = """# Compare the two DAC types.

| Parameter | Binary weighted DAC | R-2R ladder DAC |
|---|---|---|
| Resistor values | $n$ different values | Only $R$ and $2R$ |
| Accuracy | Poor above about 8 bits | Good |
| Cost | Higher for many bits | Lower |
"""
    crops = []
    for style in ("grid", "shaded"):
        res = server.create_document(template="assignment", title="T", filename=f"tab_{style}", body_markdown=body,
                                     table_style=style, skip_planning=True)
        p = Image.open(pages(res["docx"], f"tab{style}")[1])
        crops.append(card(p.crop((50, 55, p.width - 50, 360)), 600,
                          "Default: plain Word table" if style == "grid" else 'Optional: table_style="shaded"'))
    save(row(crops), "tables.png")

    thumbs = []
    for w, st, label in ((0.5, "single", "0.5 pt single (default)"), (1.5, "single", "1.5 pt single"),
                         (3, "double", "3 pt double"), (2.25, "thick-thin", "2.25 pt thick-thin")):
        res = server.create_document(template="assignment", title="Sample", filename=f"b{w}{st}", body_markdown="# Q\n\nAnswer text.\n",
                                     border_width_pt=w, border_style=st, skip_planning=True)
        thumbs.append(card(Image.open(pages(res["docx"], f"b{w}{st}".replace(".", "_"))[0]), 230, label))
    save(row(thumbs), "page-borders.png")


def sample_pages() -> None:
    refs = [
        {"key": "razavi1995", "type": "book", "authors": ["Behzad Razavi"], "title": "Principles of Data Conversion System Design",
         "publisher": "IEEE Press", "address": "New York, NY, USA", "year": 1995},
        {"key": "sedra2015", "type": "book", "authors": ["Adel S. Sedra", "Kenneth C. Smith"], "title": "Microelectronic Circuits",
         "edition": 7, "publisher": "Oxford Univ. Press", "address": "New York, NY, USA", "year": 2015},
        {"key": "kester2005", "type": "book", "authors": ["Walt Kester"], "title": "The Data Conversion Handbook",
         "publisher": "Newnes", "address": "Burlington, MA, USA", "year": 2005},
    ]
    res = server.create_document(
        template="assignment", title="Assignment on Digital to Analog Conversion Techniques", filename="sample",
        module="ET2013 – Analog Electronics", submission_date="17/05/2026", references=refs, skip_planning=True,
        body_markdown=(ROOT / "examples" / "full_assignment.md").read_text(encoding="utf-8"),
    )
    imgs = [Image.open(p_) for p_ in pages(res["docx"], "sample")]
    save(row([card(i, 430) for i in imgs[:3]], gap=20), "sample-pages.png")
    for name, img in zip(("cover", "question-1", "question-2", "references"), imgs):
        save(card(img, 620), f"page-{name}.png")
    figs = sorted(Path(res["figures_folder"]).glob("*.png"))
    h = 300
    strip = [Image.open(f).convert("RGB") for f in figs]
    strip = [f.resize((int(f.width * h / f.height), h), Image.LANCZOS) for f in strip]
    save(row(strip, gap=40), "generated-figures.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    sample_pages()
    architecture()
    workflow()
    live_editing()
    plots()
    circuits()
    diagrams()
    equations()
    tables_and_borders()
    shutil.rmtree(WORK, ignore_errors=True)
