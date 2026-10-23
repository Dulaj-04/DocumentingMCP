# KDU EE Report Style Spec

Reverse-engineered from three sample submissions (General Sir John Kotelawala Defence University,
Dept. of Electrical, Electronic and Telecommunication Engineering, Intake 42). This is the target
the MCP server must reproduce.

| Sample | Kind | Module |
|---|---|---|
| `Lab_4__EE-0008.pdf` | Lab report | ET2263 Embedded Systems (STM32 + I2C LCD) |
| `INTAKE42_EE2023_ENG_D_25_0008.docx` | Continuous assessment (CA) report | EE2263 Electrical Motors in Industry (PSCAD sim) |
| `D_Wickramanayake_..._25_0030.pdf` | Question-and-answer assignment | ET2013 Analog Electronics (DACs) |

All three were authored in MS Word, so the output must be **.docx** (with optional PDF export).

## 1. Page setup (all document types)

| Property | Value |
|---|---|
| Paper | US Letter, 8.5 × 11 in (612 × 792 pt) |
| Margins | top 0.75 in, left/right/bottom 0.79 in (1080 / 1134 twips) |
| Page border | single black line, 1 pt (`w:sz=8`), all four sides, **every page including the cover** |
| Border spacing | 1 pt top/bottom, 4 pt left/right from text |
| Header/footer | none, no page numbers |
| Paragraph defaults | 8 pt after, ~1.08 line spacing (Word default `after=160, line=259`) |

## 2. Cover page (shared by all types)

Top to bottom, everything centered unless noted:

1. **University crest**, about 2.1 in wide × 1.6 in tall, centered, with roughly 1.3 in of space above it.
2. `GENERAL SIR JOHN KOTELAWALA DEFENCE UNIVERSITY`: Times New Roman 14 pt bold, all caps.
3. `DEPARTMENT OF ELECTRICAL ELECTRONIC AND` / `TELECOMMUNICATION ENGINEERING`: same style, two lines.
4. Blank gap, then the module line `<CODE> – <MODULE NAME>` (for example `ET2263 – EMBEDDED SYSTEMS`): 14 pt bold caps, **en dash**.
5. Large gap, then the **title**: Times New Roman 22 pt bold, Title Case, may wrap to two lines with generous line spacing.
   - Variant: the assignment sample used a condensed display face (Agency FB Bold) for the title. Make it configurable.
6. Large gap, then the **details block**, left-aligned and indented about 0.5 in from the margin, Times New Roman 12 pt, one line each with spacing between them:
   ```
   Name ; W M L M Herath
   Reg No ; D/ENG/EE/25/0008
   Intake ; 42
   Submission Date ; 31/08/2026
   ```
   - The samples used ` ; ` or ` : ` separators. **Decision: no separator.** Labels are plain, values are
     **bold**, and the values are aligned with a tab stop at 2.1 in.
   - Date format is `DD/MM/YYYY`.
7. Page break.

## 3. Body typography

| Element | Lab report | CA report | Assignment |
|---|---|---|---|
| Body font | Calibri 11–12 pt | Times New Roman 12 pt | Times New Roman 12 pt |
| Body alignment | justified | justified | justified |
| Section heading | **centered, ALL CAPS, underlined, not bold**, Calibri ~14 pt | **left, Title Case, bold + underlined**, Times New Roman 16 pt | numbered question (see §6) |
| Sub-heading | underlined, left, ~12–13 pt | bold underlined 14 pt, or `1. Phase Current` numbered plain | **bold + underlined**, left, 12 pt |
| Math font | Cambria Math (native Word equations) | same | same |

## 4. Lab report structure (`lab_report`)

**Lab header block: not required.** The user confirmed that the page-2 block below (banner, lab title
line, Reg No and name, and the info box) is not a necessary part. The lab report goes straight from
the cover to `AIM`. We record the block here for reference only. It may be added later as an opt-in
(`include_lab_header=False` by default).

- A two-cell banner, full width, with top and bottom rules:
  - Left cell: small crest (about 1 in).
  - Right cell, light-grey shading (`#F2F2F2`), centered, Cambria ~13 pt, three lines:
    `General Sir John Kotelawala Defence University` / `Faculty of Engineering` / `Electronic Laboratory`
- `Lab <N>: <Title>`: Calibri bold 12 pt.
- `<Reg No>`, then `<Name>` in the form `W.M.L.M Herath`: bold, blue `#4472C4`, ~13 pt, one per line.
- **Lab info box**: a single-border table with three columns (label | `:` | value) and no inner grid lines. Labels are bold, Times New Roman 11 pt:
  - Module code and name
  - Name of the lab class
  - Duration
  - Related Learning Outcome of the module
  - Scope of the lab class: "By the end of this practical work, a student should be able to:" followed by a lower-roman list (i., ii., iii.)

**Sections, in order.** Each heading is centered, all caps and underlined:

`AIM` → `APPARATUS` → `THEORY` → `PROCEDURE` → `OBSERVATION` → `RESULT` → `CODE` → `DISCUSSION` → `CONCLUSION`

- AIM and APPARATUS: bullet (•) lists.
- THEORY: justified prose paragraphs. Key values are bolded inline, for example **MD2 = 1, MD1 = 0, MD0 = 0 resulted in the I2C address 0x48**. Function names go in single quotes, `‘I2C_ScanBus ()’`.
- PROCEDURE: numbered list (1., 2., …), past tense, passive voice.
- OBSERVATION: underlined sub-headings (for example "Memory Inspection of Message Buffers") plus full-width screenshots.
- RESULT: a left-aligned underlined heading (Times New Roman), one bullet sentence, then a centered photo of the hardware (about 60% of the width).
- CODE: the full source as plain paragraphs. The original used Calibri; **we will use a monospace font (Consolas 9–10 pt) in a light box**, which is a deliberate upgrade.
- DISCUSSION and CONCLUSION: justified prose, past tense, passive voice.

## 5. CA / simulation report structure (`ca_report`)

Left-aligned, bold, underlined Times New Roman 16 pt headings, for example:

`Objectives` → `Given Data` → `Per-Unit Base Values` → `Assumptions Made` → `<Tool> Model Description` → `Result and Observation` → (per-quantity numbered sub-sections: `1. Phase Current`, `2. …`) → `Effect of <Parameter> Variation` → `Discussion` → `Conclusion`

- Given Data: a two-column table (`Parameters` | `Given Value`) with style **Table Grid** (all borders, 0.5 pt black), plain header row, Times New Roman 12 pt, inset about 0.15 in from the margin.
- Per-unit values: aligned `Label : Symbol_sub = equation = value unit` lines with **inline Word equations** and subscripts (`S_base`, `V_base`).
- Assumptions: a decimal numbered list.
- Results: a simulation plot (waveform image, x-axis "Time (s)"), then bullet-point observations under each plot.
- Screenshots of the tool dialogs (PSCAD/MATLAB), placed in pairs or side by side.

## 6. Q&A assignment structure (`assignment`)

- Each question is a **top-level numbered list item** (`1.`, `2.`, `3.`) containing the full question text, Times New Roman 12 pt, **not bold**.
- The answer follows as indented justified paragraphs.
- Sub-topics use **bold underlined** headings (for example "Significance in Contemporary Electronic Systems" or "Working Principle"), sometimes inside a • bullet ("• Binary Weighted Resistor DAC").
- Definition bullets follow the pattern **Bold Term -** description text.
- Equations are centered display equations (native Word OMML) and may carry a note line underneath (for example "MSB - V₁ term   LSB - Vₙ term").
- Diagrams are centered, full content width.
- Comparison tables use a grid.
- Content ends with a References list (IEEE-style numbered references are recommended).

## 7. Common conventions

- Bullets: round `•`, with a hanging indent of about 0.25 in.
- Units have a space before them (`400 V`, `50 Hz`, `0.05 pu`).
- Register number format: `D/ENG/EE/25/0008` (programme code EE or ET).
- Figures have **no captions** in the samples. Captions (`Figure n: …`) will be an optional upgrade, off by default.
- Avoid the typos in the samples (`DISSCUSSION`, `votage`). Generated text must be spell-checked.

## 8. Implications for the MCP server

- Generate .docx with python-docx. Page borders, shading and OMML equations need direct XML (`w:pgBorders`, `w:shd`, `m:oMath`).
- Equations: accept LaTeX and convert it to OMML (LaTeX → MathML → OMML via the MS `MML2OMML.XSL`, or via pandoc).
- Ship three templates: `lab_report`, `ca_report` and `assignment`. They share the cover builder and page setup.
- Profile data (name, reg no, intake, crest image) should be stored once and reused.
- PDF export through headless LibreOffice. Note that LibreOffice misplaces floating images, so all images must be **inline**.
