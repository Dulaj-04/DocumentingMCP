# Changelog

## 1.1.0

**Live editing in Word (Windows)**
- `open_in_word` opens a document in desktop Word (2013 or later, including Microsoft 365).
- While a document is open in Word, `update_section`, `insert_section`, `delete_section` and
  `replace_text` change it in place: only the affected section is swapped for a freshly built copy,
  then Word refreshes fields and saves. Hand edits elsewhere are kept.
- `export_pdf` uses the open window instead of starting a second copy of Word.
- Hand-edit guard: if a closed document was changed in Word after it was generated, a rebuild stops
  and asks first (`overwrite_manual_edits=true` to go ahead).

## 1.0.0

First complete release.

**Workflow**
- Plan-first conversation. It starts with a requirements checklist and the defaults to confirm or
  change, asks all its questions at once, and agrees a step plan with you before writing. After that
  it checks in after every step. The checklist appears as a form in apps that support MCP elicitation.
- "Get my input here". You tick the sections where you want to add your own input. The AI asks
  targeted questions (results, problems, conclusions), keeps your answers word for word and builds
  those sections around them. Ticked sections can't be written without your input.
- Every generated figure gets a critical review, and you approve it before it counts as final.

**Documents**
- KDU house style: cover, page border (0.25–6 pt; single, double, thick-thin, dotted, dashed or
  none) and page numbers (on by default, never on the cover). Templates: `assignment`,
  `lab_report`, `ca_report`.
- Group cover with a members table; the department can be set per document.
- Native Word equations from LaTeX with ISO 80000-2 typesetting, numbering, aligned derivations and
  `|x|` delimiters.
- Plots, block diagrams, flowcharts, circuits and logic gates drawn from text.
- Plain Word tables (shaded style optional), IEEE references (books, articles, conference papers,
  preprints, web pages, datasheets…), live captions and cross-references, and an optional contents page.

**Tools**
- Brief extraction; reading PDF, DOCX, XLSX, text and code; spreadsheets to tables.
- Section-level editing without regeneration.
- Pre-submission check: spelling (British forms accepted), units, placeholders, empty sections,
  limits, AI-sounding wording, figure approval and student input. Plus a similarity check against
  your own sources.
- PDF export (Word refreshes all fields first on Windows; LibreOffice otherwise).

**Fixed during testing**
- A numbered "References" heading no longer gets duplicated.
- Name suffixes (III, Jr.) are formatted correctly.
- Bar charts keep their category labels.
- Diagram edge labels no longer cover short arrows.
- The spell check ignores URLs, DOIs and plurals of known words, and skips the reference list.
