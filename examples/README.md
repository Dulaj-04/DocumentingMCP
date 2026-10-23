# Examples

These are the Markdown bodies the AI writes. You can also build one yourself to see the output.

| File | Template | Shows | Needs images? |
|---|---|---|---|
| `full_assignment.md` | `assignment` | Block diagram, plot and circuit drawn from text; equations; table; IEEE citations; cross-references | No. Everything is generated (used for the README samples) |
| `equations.md` | `assignment` | LaTeX → Word equations: subscripts, units, numbering, aligned derivations, matrices | No |
| `assignment.md` | `assignment` | The master assignment layout with a pasted block-diagram image | Yes: `dac_block_diagram.png` |
| `lab_report.md` | `lab_report` | Lab report sections, screenshot, photo, table and code listing | Yes: `debug_memory.png`, `lcd_result.png` |

The images are not included, because they come from real student work. Put your own PNGs with
those names in a folder and pass it as `assets_dir`. Missing images show up as red placeholders,
plus a warning.

To build `full_assignment.md` outside a chat (the plan step is skipped for a quick test):

```python
from pathlib import Path
from kdocs_mcp import server

server.set_profile(name="A B C Student", reg_no="D/ENG/EE/25/0000", intake="42")
server.create_document(
    template="assignment",
    title="Assignment on Digital to Analog Conversion Techniques",
    module="ET2013 – Analog Electronics",
    body_markdown=Path("examples/full_assignment.md").read_text(encoding="utf-8"),
    references=[{"key": "razavi1995", "type": "book", "authors": ["Behzad Razavi"],
                 "title": "Principles of Data Conversion System Design", "publisher": "IEEE Press", "year": 1995}],
    skip_planning=True,
)
```

Run it with `uv run python your_script.py` from the project folder. The `sedra2015` and `kester2005`
citations in `full_assignment.md` show as warnings unless you add those references too.
