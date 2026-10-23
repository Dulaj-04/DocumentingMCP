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


# --------------------------------------------------------------------------- own folder, text under images, placement


def test_profile_image_folder_is_used(home):
    mine = home / "Downloads" / "My Lab Photos"
    mine.mkdir(parents=True)
    import os

    os.environ.pop("KDOCS_MCP_IMAGES", None)
    server.set_profile(image_dir=str(mine))
    src = _photos(home / "phone")
    res = server.import_images([str(src[0])], names=["bench"])
    assert Path(res["imported"][0]["path"]).parent == mine


def test_descriptions_become_text_under_the_image(home):
    src = _photos(home / "phone")
    server.import_images([str(src[0])], names=["bench"], descriptions=["The lab bench with the circuit wired up"])
    listed = server.list_images()["images"][0]
    assert listed["description"].startswith("The lab bench")
    res = server.create_document(template="assignment", title="T", body_markdown="# Q1\n\nText.\n\n![The lab bench with the circuit](bench.jpg)\n", filename="cap")
    paras = [p.text for p in docx.Document(res["docx"]).paragraphs]
    assert "The lab bench with the circuit" in paras


def test_description_follows_a_rename(home):
    src = _photos(home / "phone")
    server.import_images([str(src[0])], names=["a"], descriptions=["Output waveform"])
    server.rename_image("a.jpg", "output-wave")
    assert server.list_images()["images"][0]["description"] == "Output waveform"


BODY = """# Apparatus

We used a function generator, an oscilloscope and a breadboard.

# Procedure

The RC low-pass filter was wired on the breadboard as in the circuit diagram.

The input was set to 1 kHz and the output was read from the oscilloscope.

# Observations

The output amplitude at 1 kHz was lower than the input.
"""


def test_suggestions_match_images_to_the_right_sections(home):
    src = _photos(home / "phone")
    server.import_images([str(f) for f in src], names=["rc-filter-circuit", "scope-1khz-output", "holiday-beach"],
                         descriptions=["Circuit diagram of the RC low-pass filter wired on a breadboard",
                                       "Oscilloscope trace of the filter output at 1 kHz", "Friends at the beach"])
    out = server.suggest_image_placement(body_markdown=BODY)
    by_section = {s["section"]: [c["image"] for c in s["candidates"]] for s in out["suggestions"]}
    assert "rc-filter-circuit.jpg" in by_section["Procedure"]
    assert "scope-1khz-output.jpg" in by_section["Observations"]
    assert "holiday-beach.png" in out["not_matched_anywhere"]  # irrelevant images are left out
    after = next(c for s in out["suggestions"] if s["section"] == "Procedure" for c in s["candidates"] if c["image"].startswith("rc-"))
    assert "RC low-pass" in after["after_text"]


def test_place_image_inserts_after_the_chosen_paragraph(home):
    src = _photos(home / "phone")
    server.import_images([str(src[0]), str(src[1])], names=["scope-1khz", "scope-2khz"],
                         descriptions=["Output trace at 1 kHz", "Output trace at 2 kHz"])
    res = server.create_document(template="assignment", title="T", body_markdown=BODY, filename="pl")
    out = server.place_image(res["docx"], "scope-1khz.jpg", "Procedure", after_text="input was set to 1 kHz", label="trace", confirmed=True)
    assert "error" not in out and out["placed"][0]["section"] == "Procedure"
    body = server.get_document_source(res["docx"])["body_markdown"]
    assert body.index("read from the oscilloscope") < body.index("![Output trace at 1 kHz](scope-1khz.jpg){#fig:trace}") < body.index("# Observations")
    out = server.place_image(res["docx"], "scope-1khz.jpg", "Observations", side_by_side_with=["scope-2khz.jpg"], caption="Output at two frequencies", confirmed=True)
    assert "error" not in out
    body = server.get_document_source(res["docx"])["body_markdown"]
    assert "![(a) Output trace at 1 kHz](scope-1khz.jpg){caption=\"Output at two frequencies\"} ![(b) Output trace at 2 kHz](scope-2khz.jpg)" in body
    assert "error" in server.place_image(res["docx"], "scope-1khz.jpg", "Procedure", after_text="no such words")


def test_checker_flags_an_image_with_no_text(home):
    src = _photos(home / "phone")
    server.import_images([str(src[0])], names=["bench"])
    res = server.create_document(template="assignment", title="T", body_markdown="# Q1\n\nText.\n\n![](bench.jpg)\n", filename="chk")
    report = server.check_document(res["docx"])
    assert any("no text under it" in i["message"] for i in report["issues"])


# --------------------------------------------------------------------------- sizing


from kdocs_mcp import images as image_library  # noqa: E402


def test_big_photos_are_held_back_and_big_screenshots_are_shown_wide():
    w, notes = image_library.fit_size(4000, 3000, ".jpg", 6.7)
    assert w <= 6.7 * 0.62 + 0.01 and w * 3000 / 4000 <= image_library.MAX_H_LANDSCAPE and not notes
    w, _ = image_library.fit_size(1920, 1080, ".png", 6.7)
    assert w > 6.0  # text in a screenshot must stay readable
    w, _ = image_library.fit_size(3000, 4000, ".jpg", 6.7)  # portrait phone photo
    assert w * 4000 / 3000 <= image_library.MAX_H_PORTRAIT + 0.01


def test_nothing_is_taller_than_half_a_page_whatever_the_shape():
    for size in ((900, 5000), (1080, 2400), (5000, 900), (2000, 2000)):
        w, _ = image_library.fit_size(*size, ".png", 6.7)
        assert w * size[1] / size[0] <= image_library.MAX_H_PORTRAIT + 0.05 + (0.4 if size[0] > size[1] else 0)


def test_small_images_are_not_blown_up_and_are_flagged():
    w, notes = image_library.fit_size(300, 200, ".png", 6.7)
    assert w <= 3.3 and notes and "Low resolution" in notes[0]
    w, notes = image_library.fit_size(120, 80, ".png", 6.7)
    assert w <= 3.3 and any("Very small" in n for n in notes)
    w, notes = image_library.fit_size(800, 500, ".png", 6.7)
    assert w >= 5.0 and not notes  # enough pixels to be shown large


def test_size_words_and_explicit_widths_stay_within_the_limits():
    w, _ = image_library.fit_size(3000, 2000, ".jpg", 6.7, share=image_library.SIZE_WORDS["small"])
    assert w >= 3.0  # "small" still has to be readable
    w, _ = image_library.fit_size(3000, 2000, ".jpg", 6.7, share=1.0)
    assert w <= 6.7


def test_list_images_reports_how_each_would_be_shown(home):
    src = _photos(home / "phone")
    server.import_images([str(f) for f in src], names=["a", "b", "c"])
    first = server.list_images()["images"][0]
    assert first["shown_width_in"] > 0 and first["shown_height_in"] > 0


def test_oversized_and_low_resolution_images_produce_warnings(home):
    from PIL import Image as PI

    PI.new("RGB", (300, 200), "white").save(home / "tiny.png")
    PI.new("RGB", (900, 5000), "white").save(home / "tall.png")
    md = "# Q1\n\nText.\n\n![A tiny one](tiny.png)\n\n![A tall one](tall.png){width=6in}\n"
    res = server.create_document(template="assignment", title="T", body_markdown=md, assets_dir=str(home), filename="sz")
    joined = " ".join(res["warnings"])
    assert "Low resolution" in joined and "taller than half a page" in joined
    d = docx.Document(res["docx"])
    heights = [s.height / 914400 for s in d.inline_shapes][1:]  # skip the cover crest
    assert max(heights) <= image_library.MAX_H_PORTRAIT + 0.05


# --------------------------------------------------------------------------- several images: grouping, order, confirmation, crowding

from kdocs_mcp import image_plan  # noqa: E402


def _set(home, n=4):
    folder = home / "phone"
    folder.mkdir(exist_ok=True)
    files = []
    for i in range(n):
        f = folder / f"raw{i}.png"
        Image.new("RGB", (1200, 800), "white").save(f)
        files.append(str(f))
    return files


MULTI = """# Procedure

The circuit was built on the breadboard as in the circuit diagram.

The input was set to 1 kHz and the output trace was recorded.

Then the input was set to 2 kHz and the output trace was recorded again.

# Observations

The output amplitude fell as the frequency rose.
"""


def test_a_nothing_changes_until_the_student_confirms(home):
    files = _set(home, 2)
    server.import_images(files, names=["scope-1khz", "scope-2khz"], descriptions=["Output trace at 1 kHz", "Output trace at 2 kHz"])
    res = server.create_document(template="assignment", title="T", body_markdown=MULTI, filename="cf")
    before = server.get_document_source(res["docx"])["body_markdown"]
    prev = server.place_images(res["docx"], [{"image": "scope-1khz.png", "section": "Procedure", "after_text": "1 kHz and the output"}])
    assert prev["needs_confirmation"] and prev["nothing_changed"]
    assert prev["placements"][0]["sizes"][0]["shown_width_in"] > 0
    assert prev["ask_the_student"] and "new_markdown" not in prev
    assert server.get_document_source(res["docx"])["body_markdown"] == before  # untouched
    done = server.place_images(res["docx"], [{"image": "scope-1khz.png", "section": "Procedure", "after_text": "1 kHz and the output"}], confirmed=True)
    assert "error" not in done and "scope-1khz.png" in server.get_document_source(res["docx"])["body_markdown"]


def test_several_images_keep_the_order_they_are_given_for_one_paragraph(home):
    files = _set(home, 3)
    server.import_images(files, names=["step-1", "step-2", "step-10"], descriptions=["Step one", "Step two", "Step ten"])
    res = server.create_document(template="assignment", title="T", body_markdown=MULTI, filename="ord")
    plan = [{"image": n, "section": "Procedure", "after_text": "breadboard as in"} for n in ("step-10.png", "step-1.png", "step-2.png")]
    prev = server.place_images(res["docx"], plan)
    assert [p["images"][0] for p in prev["placements"]] == ["step-10.png", "step-1.png", "step-2.png"]
    plan2 = [{**item, "order": n} for n, item in zip((3, 1, 2), plan)]  # the student chose another order
    prev2 = server.place_images(res["docx"], plan2)
    assert [p["images"][0] for p in prev2["placements"]] == ["step-1.png", "step-2.png", "step-10.png"]
    server.place_images(res["docx"], plan2, confirmed=True)
    body = server.get_document_source(res["docx"])["body_markdown"]
    assert body.index("step-1.png") < body.index("step-2.png") < body.index("step-10.png")


def test_numbered_names_sort_naturally_and_pairs_are_grouped():
    assert sorted(["scope-10.png", "scope-2.png", "scope-1.png"], key=image_plan.natural_key) == ["scope-1.png", "scope-2.png", "scope-10.png"]
    cands = [{"image": "scope-1khz.png", "description": "Trace at 1 kHz"}, {"image": "scope-2khz.png", "description": "Trace at 2 kHz"},
             {"image": "bench.png", "description": "The bench"}]
    groups = image_plan.group_candidates(cands)
    assert len(groups) == 1 and groups[0]["images"] == ["scope-1khz.png", "scope-2khz.png"]
    ba = [{"image": "wave-before.png", "description": "Waveform before filtering"}, {"image": "wave-after.png", "description": "Waveform after filtering"}]
    assert image_plan.group_candidates(ba)


def test_suggestions_include_groups_order_and_reuse(home):
    files = _set(home, 3)
    server.import_images(files, names=["scope-1khz", "scope-2khz", "breadboard-circuit"],
                         descriptions=["Output trace at 1 kHz on the oscilloscope", "Output trace at 2 kHz on the oscilloscope",
                                       "Circuit built on the breadboard"])
    out = server.suggest_image_placement(body_markdown=MULTI)
    proc = next(s for s in out["suggestions"] if s["section"] == "Procedure")
    assert proc["order_basis"] and any(set(g["images"]) == {"scope-1khz.png", "scope-2khz.png"} for g in proc["groups"])
    # the circuit photo is used in Procedure, but Observations talks about the output too: reuse is raised only if it fits
    md_used = MULTI.replace("# Observations", "![Circuit built on the breadboard](breadboard-circuit.png)\n\n# Observations")
    again = server.suggest_image_placement(body_markdown=md_used)
    assert "breadboard-circuit.png" in again["already_in_report"]


def test_stacked_images_and_crowded_sections_are_flagged(home):
    files = _set(home, 3)
    server.import_images(files, names=["a", "b", "c"])
    md = "# Results\n\nShort text.\n\n![One](a.png)\n\n![Two](b.png)\n\n![Three](c.png)\n"
    notes = image_plan.crowding(md)
    assert any("stacked" in n["message"] for n in notes) and any("only about" in n["message"] for n in notes)
    res = server.create_document(template="assignment", title="T", body_markdown=md, filename="crowd")
    report = server.check_document(res["docx"])
    assert any("stacked" in i["message"] for i in report["issues"])
    spaced = "# Results\n\n" + "\n\n".join(f"{'Words about the picture. ' * 12}\n\n![{x}]({x.lower()}.png)" for x in ("A", "B"))
    assert not any("stacked" in n["message"] for n in image_plan.crowding(spaced))


def test_page_gap_estimate_notices_an_image_that_cannot_fit(home):
    files = _set(home, 1)
    server.import_images(files, names=["wide"])
    filler = "\n\n".join("A sentence of ordinary text that fills a line. " * 6 for _ in range(10))
    md = f"# Results\n\n{filler}\n\n![Wide](wide.png)\n"
    assert any("blank at the bottom" in n["message"] for n in image_plan.layout_notes(md))
    assert not image_plan.layout_notes("# Results\n\nShort.\n\n![Wide](wide.png)\n")
