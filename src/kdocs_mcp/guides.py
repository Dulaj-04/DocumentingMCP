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
| Pipe tables (`| A | B |` + `|---|---|`) | Plain Word table. Optional `Table: caption` line under it. Always use pipe tables: grid tables (`+---+`) break if one `|` is out of line |
| `![caption](path/to/image.png){width=80%}` on its own line | Centred figure. width may be %, in, cm |
| `![(a) Input](a.png){#fig:io caption="Input and output"} ![(b) Output](b.png)` on one line | Images side by side (2 or 3 per row) at the same height, with (a)/(b) labels under each. Put `caption=` and `#fig:id` on the first image for one shared "Figure n" caption |
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

## Work with the student, not for them

- **Get the student's own input.** The plan lists every section with a "get my input here" tick box.
  For each ticked section, call `ask_section_input` *before writing it*, ask the student those
  questions, and store their answer with `save_section_input`. Then write the section around their
  points: keep their numbers, the problems they hit, their reasoning and conclusions, and their
  phrasing where it reads well. Never invent measurements, observations or opinions. If something
  is missing, ask.

- Never write the whole document in one go. Use the plan from `start_assignment` and `save_plan`.
- After each step, show the result and ask before continuing.
- If something is unclear while you are working (a missing value, an ambiguous question, which
  method the lecturer expects), stop and ask instead of guessing.

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
- If the student wants to keep editing by hand, offer `open_in_word` (Windows). While the document is
  open in Word, those edit tools change it live and keep their hand edits.
- If a tool reports `manual_edits_detected`, the student changed the file in Word. Ask them whether to
  open it in Word (edits kept) or discard their edits; only then repeat with `overwrite_manual_edits=true`.

## Equipment profiles (when a report is about specific equipment)

Use this only where a section discusses particular, named items the student saw or used: motors at a
plant visit, instruments on a lab bench, a PLC, a transformer. It is not for theory sections and not
for every report. If the brief or the student's material is about specific equipment, ask the student
whether they want this layout (the `equipment_profiles` requirement), and follow their answer.

Each item gets its own sub-section:
1. A heading that names the item and its job: `## Main cooling water pump motor: TECO 1120 kW, 10-pole`.
2. A ```profile block with its data as points and its photos right there:

```profile
label: teco1120
caption: TECO 1120 kW main cooling water pump motor
data:
  - Rated output: 1120 kW
  - Supply: 6.6 kV, 50 Hz, 134 A
  - Speed: 594 rpm (10 poles)
images:
  - file: teco-1120kw-nameplate.jpeg
    caption: Nameplate
  - file: teco-1120kw-installed.jpeg
    caption: Installed motor
```

   - data: the facts from the nameplate or datasheet, one per point, with units. Only values the student
     has (mark unclear ones as such and ask them).
   - images: 1 to 3 photos of this item (nameplate, the installed machine, its panel), from the image
     library. One photo goes beside the data; two or three go in a row under it. `layout: beside` or
     `layout: below` forces either.
   - caption + label make it one numbered figure that the text refers to with `@fig:teco1120`.
3. Then the discussion of that item in normal paragraphs: what it drives, why this type suits the duty,
   how it is started and protected, calculations (slip, torque) as equations, and what was observed.

Choose the photos by the item: the nameplate of THIS motor, THIS motor installed. Never put a photo of a
different machine in an item's profile. Do not repeat the same photos elsewhere unless they support a
different point.

## Images the student gives you

The student keeps their images in a folder in Downloads (their own, or the default `KDocs Images`). If
they made a folder, save it once with `set_profile(image_dir=...)`; every image tool then uses it.

**Prepare**
1. `import_images` copies new files in (originals untouched). Images already in the folder need no import.
2. Look at every image. Give it a descriptive name (`rename_image`) and record one plain sentence of what
   it shows with `describe_image` ("Oscilloscope trace of the filter output at 1 kHz"). If you cannot tell
   what it shows, ask the student. Never guess a label for a lab photo.

**Decide whether an image belongs at all**
3. Use an image only if it does a job the words cannot: shows a setup, a measured result, a circuit, a
   screenshot of a tool, or a comparison. Do not add one just to fill space, and leave out images
   unrelated to the question or section. Tell the student which images you left out and why.
4. Run `suggest_image_placement` on the draft. It matches each image to the sections that talk about it
   and says which paragraph it follows. Treat it as advice: read the section and confirm that the text
   really refers to what the image shows.

**Decide where it goes**
5. Put the image straight after the paragraph that introduces it, never before the text has mentioned
   it, and never at the end of a section by default. Setup photos go in Apparatus or Procedure, measured
   screenshots and graphs in Observations / Results, circuit diagrams in Theory or Design, comparison
   images next to the discussion that compares them.
6. Mention every image in the text before it appears ("as shown in Figure 2"), and use `@fig:id`.
7. Put related images (input and output, before and after, two frequencies) on one line so they sit
   side by side. Two or three per row; portrait phone photos suit a row of two. Everything else is one
   image per place, centred and sized to fit.

**Size it properly**
- Do not leave sizing to chance. `list_images` shows how each image will be displayed (`shown_width_in`,
  `shown_height_in`) and any `sizing_notes`. Read them.
- Too small and the detail is lost; too large and the layout breaks. The default does this: screenshots,
  graphs and diagrams are shown wide so their text stays readable; photos are smaller; portrait and
  square images are limited by height; nothing is taller than about half a page; nothing is enlarged
  until it goes blurry.
- You may ask for a size with `{width=small|medium|large|full}` or `{width=60%}`. Choose by purpose:
  `full` for a screenshot whose small text matters, `large` for a circuit or graph, `medium` for a
  photo of a setup, `small` only for a simple icon-like image. Overly tall results are reduced
  automatically and reported.
- If a note says "Low resolution", tell the student. Ask for a larger original or a full-size
  screenshot. Never enlarge it to hide the problem.
- In a side-by-side row, each image gets a third or half of the width. Use two per row for screenshots
  with text; three is for simple pictures. Heed any warning that a row image is too small to read.
- After building, read `warnings` in the result. Fix every sizing warning before showing the student.

**Several images: plan them together, then get the student's confirmation**
- `suggest_image_placement` also returns `groups` (images that look like a set: the same thing at
  different settings, before/after, input/output), the proposed order in each section with its basis
  (`order_basis`), `could_also_fit` (an image already used that would also support another section) and
  `crowding_in_current_report`.
- Order: the order the text discusses the images, then numbered file names (`step-2` before `step-10`).
  If `order_basis` says the order is a guess, ask the student. Steps of a procedure follow the procedure.
- Keep related images together as a row; do not stack three single images with a line of text between.
  A section with many images needs text that explains each one. If the crowding notes say it is crowded,
  group images, add the explanation, or drop the weakest image.
- Reuse an image in a second place only when it really supports both sections, and say so.
- Use `place_images` for the whole plan. **Its first call changes nothing**: it returns the order, the
  paragraph each image follows, each image's size, sizing notes, crowding warnings, estimated page gaps
  and `ask_the_student`. Present that in plain words and ask about **the order, the sizes and the
  positions**. Change the plan to match the answers (`order`, `width`, `after_text`, `side_by_side_with`)
  and preview again if anything changed. Call with `confirmed=true` only after the student agrees.
  Never confirm on their behalf, and never place images without this step.
- Estimated page gaps are only estimates. If one is reported, offer the fix (a slightly smaller image, or
  a paragraph moved after it) and check the real result after `export_pdf`.

**Text under every image**
8. Every image carries a small line saying what it shows: `![Oscilloscope trace at 1 kHz](scope-1khz.png)`.
   One sentence, plain, no "this image shows". In a row each image gets (a), (b) and the row shares one
   caption.
9. Show the student the planned placements (image, section, after which paragraph) and apply them with
   `place_images` once they agree (see below). The same image may be used in more than one place if it supports both.

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
