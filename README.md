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

## Tools the AI gets

| Tool | Purpose |
|---|---|
| `get_profile` / `set_profile` | Store your name, reg no and intake once (saved in `~/.documenting-mcp/profile.json`) |
| `list_templates` | `lab_report`, `ca_report`, `assignment` |
| `get_writing_guide` | Section order, writing style and Markdown rules for a template |
| `list_files` | See the screenshots and photos in a folder so they can be placed in the report |
| `create_document` | Build the .docx (and optionally the .pdf) and return where it was saved |

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
