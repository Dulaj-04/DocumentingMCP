# Changelog

## 1.5.0

**Image sizing**
- Images are sized by what they are: screenshots, graphs and diagrams wide enough to read; photos
  smaller; portrait and square images limited by height; nothing taller than about half a page.
- Nothing is enlarged past about 110 dpi. Low-resolution images are kept at a sensible size and
  reported, and so are rows where an image is too small to read.
- `{width=small|medium|large|full}` as well as percentages and units; an over-tall request is reduced
  and reported.
- `list_images` shows how each image would be displayed and any sizing notes.
- Phone photos keep their JPEG type after being turned upright.
- The sentence that introduces an image now stays on the same page as the image.

## 1.4.0

**Using images where they fit**
- Your own image folder: `set_profile(image_dir=...)` points every image tool at the folder you made in
  Downloads (the default is still `Downloads/KDocs Images`).
- `describe_image` records what each image shows. That sentence becomes the small text under the image
  and is used to match it to the right section. Descriptions follow an image when it is renamed.
- `suggest_image_placement` matches every image with the report's sections and says which paragraph each
  follows, which images fit nowhere, which are already used and which still need a description.
- `place_image` inserts an image after a chosen paragraph, optionally side by side with others, as a
  numbered figure with a label the text can refer to.
- Every image now gets a small line of text below it (a numbered caption when figure captions are on).
- The checker flags images with no text under them.
- Writing guide: when to use an image at all, where it belongs, and how to caption it.

## 1.3.0

**Images**
- `import_images` collects screenshots and photos in `Downloads/KDocs Images` (optionally one
  sub-folder per assignment), copying them and giving each a descriptive name. Originals are untouched.
- `list_images` shows size and shape so the AI can choose a layout. `rename_image` renames a file in
  the library and can update reports that use it.
- Reports find library images by file name, so one image can be reused anywhere.
- Two or three images on one line are placed side by side at the same height with (a)/(b) labels and an
  optional shared figure caption.

## 1.2.0

**Renamed to KDocs MCP.** The package is `kdocs_mcp`, the command is `kdocs-mcp`, and the repository is
`kdocs-mcp`. If you already use it:
- Change the command in your Claude Desktop config from `documenting-mcp` to `kdocs-mcp` (and the folder
  path if you re-cloned).
- Existing documents still work: old `.docmcp.json` files are read as before, and new ones are saved as
  `.kdocs.json`.
- The old settings folder (`~/.documenting-mcp`) and `DOCUMENTING_MCP_HOME` are still picked up. New
  installs use `~/.kdocs-mcp` and `KDOCS_MCP_HOME`.

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
