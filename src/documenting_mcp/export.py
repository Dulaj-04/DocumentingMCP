"""DOCX -> PDF, and refreshing Word fields (TOC, figure numbers, cross-references).

On Windows with Microsoft Word installed, Word itself opens the file, updates every field and table
of contents, saves the .docx and exports the PDF (best fidelity). Otherwise LibreOffice is used.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

_SOFFICE_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def _soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    return next((c for c in _SOFFICE_CANDIDATES if Path(c).is_file()), None)


def _strip_update_prompt(docx: Path) -> None:
    """Remove w:updateFields (it makes Word ask a question, which would block automation)."""
    tmp = docx.with_suffix(".tmp.docx")
    with zipfile.ZipFile(docx) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/settings.xml":
                data = data.replace(b'<w:updateFields w:val="true"/>', b"")
            zout.writestr(item, data)
    tmp.replace(docx)


def _with_word(docx: Path, pdf: Path | None) -> bool:
    """Use MS Word (Windows) to update all fields, save, and optionally export a PDF."""
    if sys.platform != "win32":
        return False
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return False
    _strip_update_prompt(docx)
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(docx.resolve()), ConfirmConversions=False, ReadOnly=False, AddToRecentFiles=False, Visible=False)
        doc.Fields.Update()
        for toc in doc.TablesOfContents:
            toc.Update()
        for tof in doc.TablesOfFigures:
            tof.Update()
        doc.Save()
        if pdf is not None:
            doc.ExportAsFixedFormat(str(pdf.resolve()), 17)  # wdExportFormatPDF
        doc.Close(False)
        return pdf is None or pdf.is_file()
    except Exception:
        return False
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def refresh_fields(docx: Path) -> bool:
    """Update TOC / captions / cross-references in place. Returns False if Word is not available."""
    return _with_word(docx, None)


def to_pdf(docx: Path, out_dir: Path | None = None) -> Path:
    pdf = (out_dir or docx.parent) / (docx.stem + ".pdf")
    if _with_word(docx, pdf):
        return pdf
    soffice = _soffice()
    if not soffice:
        raise RuntimeError(
            "PDF export needs Microsoft Word (Windows) or LibreOffice. Install one, or open the .docx and "
            "use File > Save As > PDF."
        )
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf.parent), str(docx)],
        check=True,
        capture_output=True,
        timeout=240,
    )
    if not pdf.is_file():
        raise RuntimeError("LibreOffice did not produce a PDF.")
    return pdf


def page_count(pdf: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(pdf)).pages)
