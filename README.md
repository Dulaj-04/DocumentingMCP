# DocumentingMCP

An MCP server that writes **KDU Electrical & Electronic Engineering documents** (lab reports,
CA / simulation reports and question-and-answer assignments) as properly formatted Word files.

You chat with Claude or ChatGPT as usual ("write my Lab 4 report, screenshots are in
`C:\Users\User\Desktop\lab4`"). The AI writes the content, and this server applies the university
house style:

- The cover page: crest, university and department, module line, title, and your Name / Reg No /
  Intake / Submission Date.
- A black page border on every page, US Letter paper, and the margins used in the samples.
- Template-specific headings:
  - **lab_report**: centered, UPPERCASE, underlined Calibri (Aim → Apparatus → Theory → Procedure →
    Observation → Result → Code → Discussion → Conclusion).
  - **ca_report**: left-aligned, bold, underlined Times New Roman at 16 pt (Objectives, Given Data,
    Assumptions Made, …).
  - **assignment**: auto-numbered questions, with answers indented below them.
- Bullet and numbered lists, grid tables, centered figures (phone-photo rotation is fixed for you).
- **Real Word equations**, written in LaTeX (`$V_{out} = IR$`).
- Code listings in a monospace box.
- Optional PDF export.
- Graphs, block diagrams and circuits drawn from text; IEEE citations; captions and cross-references.
- Section-by-section editing, and a pre-submission checker.

The style rules are documented in [`docs/style-spec.md`](docs/style-spec.md).

## Equations

Write the maths in LaTeX and it becomes **native Word equations**: the same editable objects you get
from Insert → Equation, not images. They are typeset in standard scientific style (ISO 80000-2):

| You write | Word shows |
|---|---|
| `$V_{out} = V_{ref}\times\frac{D}{2^n}$` | *V*<sub>out</sub> = *V*<sub>ref</sub> × *D*/2<sup>*n*</sup>, with "out" and "ref" upright and the variables italic |
| `$V = 3.4375 V$`, `$-5V$`, `$10\mu F$`, `$2.2 k\Omega$` | Upright units with a thin space: 3.4375 V, −5 V, 10 µF, 2.2 kΩ |
| `$b_{n-i}$`, `$x_{ij}$` | Index subscripts stay italic |
| `$$ ... \tag{1}$$`, or `number_equations=true` | The equation is centered with "(1)" flush right |
| `\begin{aligned} ... &= ... \\ &= ... \end{aligned}` | A multi-line derivation with the = signs aligned |

Fractions, roots, sums, integrals, limits, matrices, `cases`, overbars, accents, `\angle`, degrees and
siunitx (`\SI{5}{\kilo\ohm}`) are all supported. See [`examples/equations.md`](examples/equations.md).

## Graphs, diagrams and circuits

Write them as fenced blocks in the body and they are drawn for you, in the document's colours:

- ```` ```plot ```` draws an engineering graph from data, a formula, or Excel/CSV columns. Line, scatter, step,
  stem and bar plots are supported, with log axes, annotations and `$maths$` in labels.
- ```` ```diagram ```` draws a block diagram or flowchart from Mermaid syntax (`A[Latch] --> B[Switch]`). The
  layout is automatic, and feedback loops are routed around the outside.
- ```` ```circuit ```` draws a circuit or logic diagram (resistors, sources, op-amps, transistors, gates…).

See [`examples/full_assignment.md`](examples/full_assignment.md).

## Citations, captions and cross-references

- `[@razavi1995]` becomes **[1]**, and an **IEEE reference list** is generated under `# References`.
  References come from a saved library, filled from a DOI, ISBN or URL (`lookup_reference`) or added manually.
- Label things with `{#fig:x}`, `{#tbl:x}` or `\label{eq:x}`, then write `@fig:x`, `@tbl:x` or `@eq:x`. They
  become **live Word cross-references**: "Figure 2", "Table 1", "Eq. (3)".

## Tools the AI gets

| Area | Tools |
|---|---|
| Profile | `get_profile`, `set_profile`: your name, reg no and intake, stored once |
| Writing | `list_templates`, `get_writing_guide`, and `create_document` (builds the .docx/.pdf) |
| Source material | `extract_assignment_brief` (pulls the questions, marks, module and due date from a brief), `read_source` (PDF/DOCX/XLSX/TXT/code), `list_files`, `spreadsheet_to_table` |
| Visuals | `make_plot`, `make_diagram`, `make_circuit` (previews; the same specs work as body blocks) |
| References | `lookup_reference` (DOI/ISBN/URL), `add_reference`, `list_references`, `remove_reference` |
| Editing | `get_document_source`, `update_section` (by heading or `Q2`), `insert_section`, `delete_section`, `replace_text`, `update_document_settings`. Only the changed part moves; formatting stays in the master style. |
| Checking | `check_document`, which reports typos (British spelling is accepted), placeholders, "5V"-style unit spacing, first-person writing, empty sections, missing images, broken citations and cross-references, unanswered questions, and word/page limits. `check_similarity` flags paragraphs copied too closely from the lecture notes. |
| Output | `export_pdf`. With Word on Windows, it refreshes the TOC, numbering and cross-references first. |

**Optional extras.** These are all off by default, because the master format doesn't use them:
`toc`, `list_of_figures`, `list_of_tables`, `page_numbers` ("bottom-center" / "bottom-right"; the cover
is never numbered), `header_text`, `footer_text`, `figure_captions` and `number_equations`.

By default, documents are saved to `Documents\DocumentingMCP`. You can change this with `set_profile(output_dir=...)`.

## Install (Windows)

1. Install **uv** (the Python package manager). Run this once in PowerShell:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. Clone this repo, or pull the latest changes:
   ```powershell
   cd C:\Users\User\clauderemote
   git clone https://github.com/Dulaj-04/DocumentingMCP.git
   ```
3. Test that it starts. Press Ctrl+C to stop it:
   ```powershell
   uv --directory C:\Users\User\clauderemote\DocumentingMCP run documenting-mcp
   ```

PDF export uses Microsoft Word if it is installed, or LibreOffice otherwise.

## Use with Claude Desktop

Open Claude Desktop, go to **Settings → Developer → Edit Config**, and add the following to
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "documenting-mcp": {
      "command": "uv",
      "args": ["--directory", "C:\\Users\\User\\clauderemote\\DocumentingMCP", "run", "documenting-mcp"]
    }
  }
}
```

Restart Claude Desktop. Then ask, for example: *"Set my profile: W M L M Herath, D/ENG/EE/25/0008,
intake 42. Then write my ET2263 Lab 4 report on interfacing a 16x2 LCD with STM32 over I2C. My
screenshots are in C:\Users\User\Desktop\lab4."*

## Use with ChatGPT Desktop

ChatGPT connects only to MCP servers reachable over **HTTPS**; it cannot launch local programs the
way Claude Desktop does. So you run the server in HTTP mode and expose it with a tunnel:

1. Start the server:
   ```powershell
   uv --directory C:\Users\User\clauderemote\DocumentingMCP run documenting-mcp --transport http --port 8000 --allowed-host YOUR-TUNNEL-DOMAIN
   ```
2. In a second PowerShell window, start a tunnel. For example, with Cloudflare's free quick tunnel:
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
   It prints a URL such as `https://something.trycloudflare.com`. Use that domain as
   `YOUR-TUNNEL-DOMAIN` in step 1 (without `https://`), then restart the server.
3. In ChatGPT, turn on **Developer mode** under Settings → Apps & Connectors → Advanced. Create a
   connector with the URL `https://something.trycloudflare.com/mcp`. The menu names may differ
   slightly between ChatGPT versions.

The files are still saved on **your PC**, because the server runs there.

> ⚠️ While the tunnel is open, anyone who knows the URL can call the tools. Close the tunnel when
> you are done.

## Writing the body (for reference)

The AI receives these rules through `get_writing_guide`, but you can also write Markdown yourself.
See [`examples/lab_report.md`](examples/lab_report.md) and [`examples/assignment.md`](examples/assignment.md).

````markdown
# Theory
The output is $V_{out} = V_{ref} \times \frac{D}{2^n}$.

$$V_{out} = -V_{ref}\sum_{i=1}^{n} b_{n-i}\,2^{-i}$$

- **Bold term** - explanation
1. Numbered step

| Parameters | Given Value |
|---|---|
| Rated Voltage | 400 V |

![LCD output](lcd_result.jpg){width=60%}

```c
HAL_I2C_Master_Transmit(&hi2c2, addr << 1, &cmd, 1, HAL_MAX_DELAY);
```

<!-- pagebreak -->
````

## Development

```bash
uv sync
uv run pytest
```
