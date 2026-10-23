"""Live editing in Word, tested against a small stand-in for Word's COM objects (Word itself only runs on
Windows). The stand-in keeps the document as plain text with '\r' paragraph marks, like Range.Text."""

import re
from pathlib import Path

import docx
import pytest

from kdocs_mcp import live_word, project, server


class FakeFind:
    def __init__(self, rng):
        self.rng = rng
        self.Replacement = self

    def ClearFormatting(self):
        pass

    def Execute(self, FindText, ReplaceWith, Replace, **_kw):
        doc, text = self.rng.doc, self.rng.doc.text
        n = -1 if Replace == live_word.WD_REPLACE_ALL else 1
        head, body, tail = text[: self.rng.Start], text[self.rng.Start : self.rng.End], text[self.rng.End :]
        doc.text = head + body.replace(FindText, ReplaceWith, n) + tail
        return True


class FakeRange:
    def __init__(self, doc, start, end):
        self.doc, self.Start, self.End = doc, start, end

    @property
    def Text(self):
        return self.doc.text[self.Start : self.End]

    @property
    def FormattedText(self):
        return self.Text

    @FormattedText.setter
    def FormattedText(self, value):
        self.doc.text = self.doc.text[: self.Start] + value + self.doc.text[self.End :]

    def Delete(self):
        self.FormattedText = ""

    @property
    def Find(self):
        return FakeFind(self)


class FakeParagraph:
    def __init__(self, rng, level):
        self.Range, self.OutlineLevel = rng, level


class FakeCollection:
    def __init__(self, items):
        self.items = items
        self.Count = len(items)

    def Item(self, i):
        return self.items[i - 1]

    def __iter__(self):
        return iter(self.items)


class FakeApp:
    def __init__(self):
        self.opened = []
        self.Documents = self

    def Open(self, path, **_kw):
        d = FakeDoc.from_docx(Path(path), self)
        self.opened.append(d)
        return d


class FakeDoc:
    def __init__(self, paragraphs, app=None, path=None):
        self.text = "".join(t + "\r" for t, _ in paragraphs)
        self.levels = {t: lvl for t, lvl in paragraphs if lvl < live_word.BODY_LEVEL}
        self.Application = app or FakeApp()
        self.FullName = str(path) if path else "fake.docx"
        self.saved = self.closed = 0
        self.Fields = self
        self.TablesOfContents = []

    @classmethod
    def from_docx(cls, path, app=None):
        paras = []
        for p in docx.Document(str(path)).paragraphs:
            m = re.match(r"Heading (\d)", p.style.name or "")
            paras.append((p.text, int(m.group(1)) if m else live_word.BODY_LEVEL))
        return cls(paras, app, path)

    @property
    def Paragraphs(self):
        out, pos = [], 0
        for t in self.text.split("\r")[:-1]:
            out.append(FakeParagraph(FakeRange(self, pos, pos + len(t) + 1), self.levels.get(t, live_word.BODY_LEVEL)))
            pos += len(t) + 1
        return FakeCollection(out)

    @property
    def Content(self):
        return FakeRange(self, 0, len(self.text))

    def Range(self, start, end):
        return FakeRange(self, start, end)

    def Update(self):
        pass

    def Save(self):
        self.saved += 1
        Path(self.FullName).write_text(self.text, encoding="utf-8")

    def Close(self, _save=False):
        self.closed += 1


def _sample():
    return FakeDoc([
        ("Q1", 1), ("Answer one.", 10), ("Part a", 2), ("Detail.", 10),
        ("Q2", 1), ("Answer two.", 10), ("References", 1), ("[1] A book.", 10),
    ])


# --------------------------------------------------------------------------- live_word on its own


def test_section_span_stops_at_next_heading_of_same_level():
    d = _sample()
    s, e = live_word.section_span(d, "Q1")
    assert d.Range(s, e).Text == "Q1\rAnswer one.\rPart a\rDetail.\r"
    s, e = live_word.section_span(d, "part a")
    assert d.Range(s, e).Text == "Part a\rDetail.\r"
    assert live_word.section_span(d, "Nope") is None


def test_last_section_keeps_final_paragraph_mark():
    d = _sample()
    s, e = live_word.section_span(d, "References")
    assert e == len(d.text) - 1


def test_delete_and_replace_text_live():
    d = _sample()
    assert live_word.delete_section_live(d, "Q2")
    assert "Q2" not in d.text and "References" in d.text
    assert live_word.replace_text_live(d, "Answer", "Reply") == 1
    assert "Reply one." in d.text
    d2 = FakeDoc([("x x x", 10)])
    assert live_word.replace_text_live(d2, "x", "y", count=2) == 2
    assert d2.text == "y y x\r"


# --------------------------------------------------------------------------- through the server tools


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("KDOCS_MCP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KDOCS_MCP_REQUIRE_PLAN", "0")
    server.set_profile(name="A B C Student", reg_no="D/ENG/EE/25/0000", intake="42", output_dir=str(tmp_path / "out"))
    return tmp_path


BODY = "# Introduction\n\nFirst part.\n\n# Results\n\nThe gain was 10.\n\n# Discussion\n\nIt worked.\n"


@pytest.fixture
def open_doc(monkeypatch):
    """Create a document, then pretend the student opened it in Word and typed a note into it."""
    res = server.create_document(template="lab_report", title="Lab", body_markdown=BODY, filename="lab")
    path = Path(res["docx"])
    word = FakeDoc.from_docx(path)
    word.text = word.text.replace("First part.\r", "First part.\rMY HAND EDIT\r")
    monkeypatch.setattr(live_word, "find_open_document", lambda p, app=None: word if Path(p) == path else None)
    return path, word


def test_update_section_goes_into_the_open_document(open_doc):
    path, word = open_doc
    out = server.update_section(str(path), "Results", "The gain was 12.")
    assert out.get("live") is True, out
    assert "The gain was 12." in word.text and "The gain was 10." not in word.text
    assert "MY HAND EDIT" in word.text  # the student's own edit survives
    assert word.saved == 1 and all(d.closed for d in word.Application.opened)
    assert project.load_source(path).built_hash == project.file_hash(path)


def test_insert_delete_and_replace_live(open_doc):
    path, word = open_doc
    assert server.insert_section(str(path), "# Method\n\nWe measured it.", after="Introduction").get("live")
    assert word.text.index("Method") < word.text.index("Results")
    assert server.delete_section(str(path), "Discussion").get("live")
    assert "It worked." not in word.text
    assert server.replace_text(str(path), "gain", "voltage gain").get("live")
    assert "voltage gain" in word.text and "MY HAND EDIT" in word.text


def test_whole_document_changes_need_the_document_closed(open_doc):
    path, _ = open_doc
    assert "error" in server.update_document_settings(str(path), border_width_pt=1.0)


def test_hand_edits_are_not_overwritten_when_closed(home):
    res = server.create_document(template="lab_report", title="Lab", body_markdown=BODY, filename="lab")
    path = Path(res["docx"])
    blocked = server.update_section(str(path), "Results", "The gain was 12.")
    assert "error" not in blocked  # untouched since it was built: rebuild is fine
    path.write_bytes(path.read_bytes() + b"\0")  # stands in for a save from Word
    blocked = server.update_section(str(path), "Results", "The gain was 13.")
    assert blocked.get("manual_edits_detected")
    ok = server.update_section(str(path), "Results", "The gain was 13.", overwrite_manual_edits=True)
    assert "error" not in ok
    assert "The gain was 13." in "\n".join(p.text for p in docx.Document(str(path)).paragraphs)
