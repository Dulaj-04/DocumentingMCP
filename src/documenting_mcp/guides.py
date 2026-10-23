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

Image paths may be absolute, or relative to `assets_dir`. Use `list_files` to see what images the
student has. Never invent image paths. If a required screenshot or photo is missing, write a short
italic placeholder such as `*[Insert photo of the LCD output here]*`.

Writing style for all KDU EE reports:
- Formal academic English, in the **past tense and passive voice** for procedure, observations,
  discussion and conclusion (for example "The LCD was initialised…", "It was observed that…").
- Put a space between a number and its unit (`400 V`, `50 Hz`, `0.05 pu`). Use SI units.
- Refer to functions and identifiers in single quotes or as `code`.
- Proof-read. Sample reports contained typos ("DISSCUSSION", "votage"), so do not reproduce them.
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
# Template: assignment (question-and-answer)

Each top-level `# heading` is ONE QUESTION. Paste the full question text as the heading. It is
numbered automatically (1., 2., 3., …), so do not type the number yourself. Answer under it:

- Justified answer paragraphs.
- `## Sub-topic` headings (rendered bold and underlined), for example "Working Principle",
  "Advantages", "Limitations".
- Definition bullets in the form `- **Term** - explanation`.
- Display equations for every formula, followed by a "where …" sentence defining the symbols.
- Diagrams with `![...](path)` where the question asks for a diagram. If you have no image, insert
  an italic placeholder describing the diagram needed.
- Comparison questions should use a pipe table.

End with `# References` (it is recognised and NOT numbered as a question), followed by an IEEE-style
numbered list.
""",
}


def guide_for(template: str) -> str:
    return GUIDES[template] + "\n" + MARKDOWN_RULES
