"""DOCX -> PDF. Uses MS Word on Windows when available (best fidelity), else LibreOffice."""

from __future__ import annotations

import shutil
import subprocess
import sys
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


def to_pdf(docx: Path) -> Path:
    pdf = docx.with_suffix(".pdf")
    if sys.platform == "win32":
        try:
            from docx2pdf import convert  # needs MS Word installed

            convert(str(docx), str(pdf))
            if pdf.is_file():
                return pdf
        except Exception:
            pass
    soffice = _soffice()
    if not soffice:
        raise RuntimeError(
            "PDF export needs Microsoft Word (Windows) or LibreOffice. Install one, or open the .docx and "
            "use File > Save As > PDF."
        )
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
        check=True,
        capture_output=True,
        timeout=180,
    )
    if not pdf.is_file():
        raise RuntimeError("LibreOffice did not produce a PDF.")
    return pdf
