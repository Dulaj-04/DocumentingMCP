"""Writing guides returned to the model so it produces content in the house style."""

from __future__ import annotations

MARKDOWN_RULES = """\
## How to write the body (Markdown)

The cover page is generated automatically. Do NOT write the university name, title, name, reg no,
intake or date in the body.

| You write | You get |
|---|---|
| `# Heading` | Section heading, styled for the template |
| `## Sub-heading` / `### Minor heading` | Sub-headings |
| `**bold**`, `*italic*`, `` `code` `` | Inline formatting |
| `- item` / `1. item` (indent 4 spaces to nest) | Bullet (•) / numbered lists; each list restarts |
| `**Term** - description` inside a bullet | The "bold term - definition" style |
| `$V_{out} = IR$` | Inline Word equation (LaTeX syntax) |
| `$$V_{out} = -V_{ref}\\sum_{i=1}^{n} b_{n-i}\\,2^{-i}$$` on its own line | Centred display equation |
| Pipe tables (`| A | B |` + `|---|---|`) | Grid table. Optional `Table: caption` line under it |
| `![caption](path/to/image.png){width=80%}` on its own line | Centred figure. width may be %, in, cm |
| Fenced code block (```` ```c ````) | Monospace code listing in a light box |
| `<!-- pagebreak -->` | Page break |

## Equations (converted to native, editable Word equations)

Write standard LaTeX math. Every equation becomes a real Word equation (Insert → Equation), not an
image, so the student can still edit it in Word.

- Display equations go on their own line: `$$ ... $$`. Inline ones use `$ ... $` inside a sentence.
- Introduce each display equation with a lead-in line and follow it with "where …" defining every symbol.
- Scientific typesetting (ISO 80000-2) is applied automatically:
  - Descriptive subscripts become upright: `V_{out}`, `V_{ref}`, `I_{CE}`, `V_{rms}` → V_out with "out" upright.
  - Index subscripts stay italic: `b_{n-i}`, `x_{ij}`, `R_{k}`.
  - Numbers with units get an upright unit and a thin space: `5 V`, `10 kHz`, `4.7\mu F`, `2.2 k\Omega`.
  - Variables stay italic.
- Use `\text{...}` for words inside equations (`\text{Digital Code}`) and `\times` or `\cdot` for multiplication.
- Supported: `\frac`, `\dfrac`, `\sqrt[n]{}`, `\sum`, `\int`, `\lim`, `\left( \right)`, matrices
  (`bmatrix`, `pmatrix`), `cases`, `\overline` (logic NOT), `\hat`, `\vec`, `\dot`, `\angle`,
  `^{\circ}`, Greek letters, `\sin`, `\cos`, `\log`, `\ln`, `\max`.
- Multi-step derivations: use `\begin{aligned} V_{out} &= ... \\ &= ... \end{aligned}` so the `=` signs line up.
- Equation numbers: add `\tag{1}` to a display equation, or pass `number_equations=true` to number all
  of them (and use `\notag` to skip one). The number appears flush right as "(1)".
- siunitx is accepted: `\SI{5}{\kilo\ohm}` and `\si{\milli\ampere}`.

## Graphs, block diagrams and circuits (drawn for you, inside the body)

Write these as fenced blocks. Each one is rendered to a figure in the document's colours. Add
`#fig:name` and `caption="..."` to number it and refer to it.

````markdown
```{.plot #fig:torque caption="Torque–slip characteristic for two rotor resistances"}
x_label: "Slip $s$"
y_label: "Torque $T_e$ (pu)"
constants: {Tm: 2.5, s1: 0.04, s2: 0.2}
series:
  - {label: "$R_r$ = 0.01 pu", expr: "2*Tm*s*s1/(s^2+s1^2)", var: s, range: [0.001, 1]}
  - {label: "$R_r$ = 0.05 pu", expr: "2*Tm*s*s2/(s^2+s2^2)", var: s, range: [0.001, 1], style: "--"}
```
````

- **Plot series:** use `x`/`y` lists of measured data, `expr` with `range` (a formula), or
  `file` with `x`/`y` column names (CSV/XLSX, relative to assets_dir).
- **Plot types:** line, scatter, step, stem, bar. Log axes: `xscale: log`. Extras: `hlines`, `vlines`, `annotations`.
- **Diagrams:** a `{.diagram #fig:x caption="..."}` block in Mermaid flowchart syntax.
  - `flowchart LR` (left to right) suits block diagrams; `flowchart TD` (top down) suits program flowcharts.
  - Shapes: `A[box]`, `B(rounded)`, `C{decision}`, `D((circle))`, `E[/input or output/]`.
  - Edges: `A --> B`, `A -->|label| B`, `A -- Yes --> B`, `A -.-> B` (dotted). Line breaks: `<br>`. Maths: `$V_{ref}$`.
- **Circuits / logic:** a `{.circuit #fig:x caption="..."}` block holding a YAML list of elements
  placed one after another. Example:
  `- {type: vsource, dir: up, label: "$V_{in}$", id: vs}` then
  `- {type: resistor, dir: right, label: "$R_1$", value: "10 kΩ"}`.
  Elements can be positioned with `at: id.anchor`, `to`/`tox`/`toy`. An opamp has anchors in1, in2 and out.
  Logic gates are and, or, not, nand, nor and xor.
- Use `make_plot`, `make_diagram` and `make_circuit` first if you want to preview a drawing.
- Draw diagrams and plots instead of describing them whenever a question says "using a suitable
  diagram", "sketch", "plot" or "draw".

## Captions and cross-references

- Label figures `![caption](img.png){#fig:lcd}` and tables (a `Table: caption {#tbl:data}` line under
  the table). Display equations take `$$ ... \\label{eq:ohm} $$`.
- In the text, write `@fig:lcd` → "Figure 2", `@tbl:data` → "Table 1", `@eq:ohm` → "Eq. (3)". These
  are live Word cross-references that update if items move.
- Labelled items are always numbered. With `figure_captions=true`, every figure with alt text gets a caption.

## Citations (IEEE)

- Cite with `[@key]` → [1]. Several at once: `[@a; @b]` → [1], [2]. With a page: `[@key, p. 45]` → [1, p. 45].
- Keys come from the reference library (`lookup_reference` with a DOI/ISBN/URL, or `add_reference`)
  or from the `references` argument of create_document.
- The numbered IEEE reference list is generated under `# References`, or appended at the end. Do not
  type the list yourself.
- Cite the lecture notes, the textbook and the datasheets that the theory comes from.

## Data tables

- Use `spreadsheet_to_table` to turn the student's Excel/CSV readings into a pipe table. Tables are
  rendered as plain Word tables (thin black grid, bold header row, no colours).

## Figures must be approved by the student

Every generated plot, block diagram, flowchart and circuit starts as **pending**.

1. Call `review_figures`. For each figure it gives the PNG and an automatic critique: missing axis
   units, text too small to read, unlabelled branches or components, no caption, not referred to.
2. Look at each image yourself and judge it critically. Is it technically correct (signs, polarities,
   axis ranges, values)? Does it answer what the question asks? Is anything cluttered or misleading?
3. Show the student every figure, with the automatic issues and your own critique, and ask whether
   to keep it or what to change.
4. Make the changes with `update_section`, then review again.
5. Call `approve_figures` **only after the student explicitly approves**. Never approve on their behalf.

PDF export and `check_document` treat unapproved figures as blocking errors. Changing a figure
later makes it pending again.

## After creating the document

- Run `check_document`, and `check_similarity` against the lecture notes if they were used.
- Fix every error with `update_section` / `replace_text` / `insert_section`. Never regenerate the
  whole document for a small change.

Image paths may be absolute, or relative to `assets_dir`. Use `list_files` to see what images the
student has. Never invent image paths. If a required screenshot or photo is missing, write a short
italic placeholder such as `*[Insert photo of the LCD output here]*`. The checker reports any
placeholders still left in.

Writing style for all KDU EE reports:
- Formal academic English, in the **past tense and passive voice** for procedure, observations,
  discussion and conclusion (for example "The LCD was initialised…", "It was observed that…").
- Put a space between a number and its unit (`400 V`, `50 Hz`, `0.05 pu`). Use SI units.
- Refer to functions and identifiers in single quotes or as `code`.
- Proof-read. Sample reports contained typos ("DISSCUSSION", "votage"), so do not reproduce them.

## Write like an undergraduate, not like an AI

The report must read as if a second-year engineering student at KDU wrote it. Lecturers notice
AI-style writing, so follow these rules strictly:

- **Plain, direct sentences.** Use the vocabulary of the lecture notes and the textbook. Mix short and
  medium-length sentences. A little repetition is fine; a thesaurus-style choice of words is not.
- **No decorative layout.**
  - No "·" or "|" separated summary lines like "**Type:** X · **LOs:** Y · **Area:** Z".
  - No emoji, no arrows (→) in prose, no "key takeaways" boxes.
  - Do not invent extra sections the brief did not ask for.
- **Bold sparingly.** Use it only where the master uses it: bold-term bullets and the occasional key
  value. Do not start every paragraph with a bold label.
- **Avoid AI vocabulary and phrasing:** delve, crucial, pivotal, vital, seamless(ly), robust, leverage,
  utilise/utilize (say "use"), harness, foster, landscape, realm, tapestry, intricate, multifaceted,
  holistic, paramount, underscore, showcase, "plays a vital/crucial role", "in today's world",
  "it is important/worth noting that", "not only … but also", "in conclusion, …".
- **Do not overuse "Furthermore" and "Moreover".** Prefer "Also", "However", "Therefore" or no
  connective at all.
- **Use few em dashes (—).** Use commas, brackets or a new sentence instead.
- **Avoid perfect symmetry.** Bullet lists do not all need three items of identical length. Do not end
  sections with a one-line summary that repeats the paragraph.
- **Keep it concrete and personal to the work.** Give the actual values, the board or software used,
  what went wrong in the lab and how it was fixed, and what the graph actually shows. A real student
  writes "the LCD did not respond at first because the address was shifted twice", not "the system
  demonstrated robust communication".
- **British spelling,** as used in Sri Lanka: initialise, analyse, behaviour, colour, centre, modelled.
- Run `check_document`. It flags AI-style wording, and those flags must be rewritten.
"""

GUIDES = {
    "lab_report": """\
# Template: lab_report

Section headings are rendered CENTERED, UPPERCASE and underlined. Write them in normal case, as in
`# Aim`. Use this order (drop a section only if it truly does not apply):

1. `# Aim`: one or two bullet points stating what the practical sets out to do.
2. `# Apparatus`: a bullet list of equipment and software (board names, modules, IDE, cables, supplies).
3. `# Theory`: three to six justified paragraphs explaining the underlying principles (protocol,
   circuit or peripheral), how they apply to this setup, and key configuration values in **bold**.
4. `# Procedure`: a numbered list of the steps actually performed, in past tense passive voice.
5. `# Observation`: `## sub-headings` for each observation (for example "Memory Inspection of
   Message Buffers"), each with screenshots or measured tables.
6. `# Result`: one or two bullet sentences stating the outcome, then a photo of the working
   hardware or the final output.
7. `# Code`: the full relevant source in a fenced code block with a language tag.
8. `# Discussion`: three to five paragraphs interpreting the results, why the design choices
   worked, problems faced and how they were solved, limitations and improvements.
9. `# Conclusion`: one paragraph restating what was achieved against the aim.
""",
    "ca_report": """\
# Template: ca_report (continuous assessment / simulation report)

Section headings are rendered left-aligned, bold and underlined, at 16 pt. A typical order:

1. `# Objectives`: bullet point(s) restating the task.
2. `# Given Data`: a two-column pipe table, `| Parameters | Given Value |`, with units.
3. `# Per-Unit Base Values` (or other derived quantities): one line per quantity, using inline
   equations, for example `Base current : $I_{base} = \\frac{S_{base}}{\\sqrt{3}V_{base}} = 144.34\\ kA$`.
4. `# Assumptions Made`: a numbered list.
5. `# <Tool> Model Description`: screenshots of the simulation model and component dialogs, plus
   a short explanation.
6. `# Result and Observation`: one `## 1. <Quantity>` sub-section per plotted quantity (Phase
   Current, Torque, Speed, …). Each has its plot and a bullet list of observations
   (transient, steady state, numbers read off the plot).
7. `# Effect of <Parameter> Variation`: a comparison across cases, ideally with a table.
8. `# Discussion`, `# Conclusion`, and `# References` (IEEE numbered style).
""",
    "assignment": """\
# Template: assignment (question-and-answer), the MASTER format

This template reproduces the master assignment (ET2013 "Assignment on Digital to Analog Conversion
Techniques"). Follow its structure:

- Each top-level `# heading` is ONE QUESTION. Paste the full question text, without a number;
  "1.", "2.", … are added automatically. Inline math is allowed in the question.
- Answer paragraphs are written directly below the question. They are rendered left-aligned and
  indented to line up with the question text.
- `## Sub-heading` gives a bold, underlined heading at the left margin, for example
  "Significance in Contemporary Electronic Systems", "Working Principle", "Advantages",
  "Limitations", "Block Descriptions:" or "Performance Parameter Analysis".
- `### Topic` gives a bulleted, bold, underlined topic heading ("• Binary Weighted Resistor DAC").
  Use it when one question covers two or more items (two circuits, two methods), with `##`
  sub-headings under each.
- Bullets: use `- **Term -** explanation` for definitions, and plain `- item` for advantages or limitations.
- Every formula is a display equation `$$...$$`, introduced by a lead-in line ("The output voltage
  is expressed as:") and followed by a "where …" sentence that defines the symbols.
- Numerical problems:
  - Start with a `**Given Data**` bold line and a bullet list of the givens.
  - Then write `**Step 1 - <what>**`, `**Step 2 - <what>**`, … as bold lines, each followed by its
    equation.
  - Finish with the boxed result in bold (`**+3.4375 V**`) and one sentence interpreting it.
- Comparison questions use a 3-column pipe table (`| Parameter | Option A | Option B |`) under a
  `## …Analysis` sub-heading. It is rendered as a plain Word grid table with a bold header row.
  Write each cell as one or two full sentences.
- Diagrams use `![...](path)` on their own line (rendered at about 92% of the page width). If no
  image exists, write an italic placeholder describing the diagram that is needed.
- End with `# References` (not numbered as a question) and an IEEE-style numbered list.
""",
}


def guide_for(template: str) -> str:
    return GUIDES[template] + "\n" + MARKDOWN_RULES
