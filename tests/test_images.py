from pathlib import Path

import docx
import pytest
from PIL import Image

from kdocs_mcp import server


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("KDOCS_MCP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KDOCS_MCP_REQUIRE_PLAN", "0")
    monkeypatch.setenv("KDOCS_MCP_IMAGES", str(tmp_path / "Downloads" / "KDocs Images"))
    server.set_profile(name="A B C Student", reg_no="D/ENG/EE/25/0000", intake="42", output_dir=str(tmp_path / "out"))
    return tmp_path


def _photos(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for name, size in (("IMG_0001.jpg", (1200, 800)), ("IMG_0002.JPG", (900, 900)), ("Screenshot (3).png", (800, 1200))):
        f = folder / name
        Image.new("RGB", size, "white").save(f)
        out.append(f)
    return out


def test_import_copies_and_renames_without_touching_originals(home):
    src = _photos(home / "phone")
    res = server.import_images([str(src[0].parent)], names=["Circuit Photo", "scope trace 1kHz", "block diagram"], project="ET2013 Lab 3")
    paths = [Path(i["path"]) for i in res["imported"]]
    assert [p.name for p in paths] == ["circuit-photo.jpg", "scope-trace-1khz.jpg", "block-diagram.png"]
    assert all(p.parent.name == "et2013-lab-3" for p in paths)
    assert all(f.exists() for f in src)  # originals untouched
    assert res["imported"][2]["shape"] == "portrait"
    listed = server.list_images("ET2013 Lab 3")["images"]
    assert len(listed) == 3


def test_wrong_number_of_names_is_ignored_with_a_note(home):
    src = _photos(home / "phone")
    res = server.import_images([str(src[0]), str(src[1])], names=["only-one"])
    assert [Path(i["path"]).name for i in res["imported"]] == ["img-0001.jpg", "img-0002.jpg"]
    assert res["problems"]


def test_duplicate_names_get_a_number(home):
    src = _photos(home / "phone")
    server.import_images([str(src[0])], names=["setup"])
    res = server.import_images([str(src[1])], names=["setup"])
    assert Path(res["imported"][0]["path"]).name == "setup-2.jpg"


def test_rename_only_inside_the_library(home):
    src = _photos(home / "phone")
    assert "error" in server.rename_image(str(src[0]), "nope")
    assert src[0].exists()


def test_rename_updates_documents_and_images_resolve_from_the_library(home):
    src = _photos(home / "phone")
    server.import_images([str(src[0])], names=["setup"])
    md = "# Q1\n\nSee @fig:s.\n\n![The bench setup](setup.jpg){#fig:s}\n"
    res = server.create_document(template="assignment", title="T", body_markdown=md, filename="r")
    assert not res["warnings"]  # found by bare name in the library
    out = server.rename_image("setup.jpg", "bench-setup", update_documents=[res["docx"]])
    assert out["renamed"] and out["documents"][0]["references"] == 1
    assert "bench-setup.jpg" in server.get_document_source(res["docx"])["body_markdown"]
    assert not out["documents"][0].get("warnings")


def test_images_on_one_line_become_an_aligned_row(home):
    src = _photos(home / "phone")
    server.import_images([str(f) for f in src], names=["a", "b", "c"])
    md = ('# Q1\n\nSee @fig:row.\n\n![(a) First](a.jpg){#fig:row caption="Three results"} ![(b) Second](b.jpg) '
          "![(c) Third](c.png)\n")
    res = server.create_document(template="assignment", title="T", body_markdown=md, filename="row")
    assert not res["warnings"]
    d = docx.Document(res["docx"])
    row = next(t for t in d.tables if len(t.columns) == 3)
    ns = {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
    extents = row._tbl.xpath(".//wp:extent")
    assert len(extents) == 3
    heights = [int(e.get("cy")) for e in extents]
    assert max(heights) - min(heights) < 400  # one common height (EMU)
    text = "\n".join(p.text for p in d.paragraphs)
    assert "Figure 1: Three results" in text or "Figure 1" in text
    assert "(a) First" in "\n".join(c.text for r in row.rows for c in r.cells)
