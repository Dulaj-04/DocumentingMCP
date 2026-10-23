import json
import types
import zipfile

import anyio
import docx
import pytest

from documenting_mcp import planning, server


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENTING_MCP_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DOCUMENTING_MCP_REQUIRE_PLAN", raising=False)  # the real, gated behaviour
    server.set_profile(name="A B C Student", reg_no="D/ENG/EE/25/0000", intake="42", output_dir=str(tmp_path / "out"))
    return tmp_path


def _call(name, args):
    res = anyio.run(server.mcp.call_tool, name, args)
    return json.loads(res.content[0].text)


def _xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode()


def test_document_is_not_written_before_a_plan_is_approved():
    r = server.create_document(template="assignment", title="T", body_markdown="# Q\n\nA.\n")
    assert "No approved plan" in r["error"]
    start = _call("start_assignment", {"request": "ET2013 DAC assignment"})
    r = server.create_document(template="assignment", title="T", body_markdown="# Q\n\nA.\n", plan_id=start["plan_id"])
    assert "No approved plan" in r["error"] and r["plan_status"] == "gathering_requirements"


def test_start_assignment_returns_checklist_defaults_and_questions():
    start = _call("start_assignment", {"request": "Write my ET2013 assignment"})
    assert "STOP" in start["instruction"]
    assert "- [x] Answer every question" in start["checklist"]
    assert "Page border thickness" in start["checklist"] and "**0.5**" in start["checklist"]
    assert "Page numbers" in start["checklist"] and "bottom-center" in start["checklist"]
    assert any("Submission date" in q for q in start["open_questions"])
    assert start["form_answered_by_student"] is False  # this test client has no forms


def test_full_plan_flow_applies_agreed_settings(home):
    start = _call("start_assignment", {"request": "ET2013 DAC assignment", "template": "assignment"})
    pid = start["plan_id"]
    r = server.save_plan(pid, steps=["Write Q1", "Review figures", "Check and export"], still_unanswered=["Word limit?"])
    assert r["status"] == "gathering_requirements"
    assert "error" in server.approve_plan(pid, "yes")  # questions still open
    r = server.save_plan(
        pid, steps=["Write Q1", "Review figures", "Check and export"],
        requirements={"plots_from_data": True}, settings={"border_width_pt": 1.5, "page_numbers": "bottom-right"},
        answers={"module": "ET2013 – Analog Electronics", "title": "DAC"},
    )
    assert r["status"] == "awaiting_approval" and "1. [ ] Write Q1" in r["plan"]
    assert "error" in server.save_plan(pid, steps=["x"], settings={"paper": "A4"})  # unknown setting rejected
    server.save_plan(pid, steps=["Write Q1", "Review figures", "Check and export"])
    assert "error" in server.approve_plan(pid, "  ")  # must quote the student
    a = server.approve_plan(pid, "yes, go ahead")
    assert a["status"] == "approved" and "step 1" in a["instruction"]

    s1 = server.update_plan_step(pid, 1, "in_progress")
    assert s1["status"] == "in_progress"
    res = server.create_document(template="assignment", title="DAC", body_markdown="# Q\n\nAnswer.\n", plan_id=pid)
    assert "error" not in res
    xml = _xml(res["docx"])
    assert 'w:sz="12"' in xml  # 1.5 pt page border from the plan
    body_footer = docx.Document(res["docx"]).sections[1].footer.paragraphs[0]
    assert "PAGE" in body_footer._p.xml and body_footer.text.startswith("\t\t")  # bottom-right
    done = server.update_plan_step(pid, 1, "done", "Q1 written")
    assert "CHECK-IN" in done["instruction"] and "step 2" in done["instruction"]
    assert planning.load(pid).docx_path == res["docx"]
    for n in (2, 3):
        server.update_plan_step(pid, n, "done")
    assert planning.load(pid).status == "done"


def test_form_answers_fill_the_plan():
    plan = planning.new_plan("lab report", "lab_report")

    class Fake:
        client_capabilities = types.SimpleNamespace(elicitation=object())

        async def elicit(self, message, schema):
            values = {name: f.default for name, f in schema.model_fields.items()}
            values.update({"include_code": True, "setting_border_width_pt": 2.25, "answer_title": "Lab 4"})
            return types.SimpleNamespace(action="accept", data=schema(**values))

    ok = anyio.run(server._ask_with_form, Fake(), plan)
    p = planning.load(plan.id)
    assert ok and p.requirements["include_code"] is True and p.settings["border_width_pt"] == 2.25
    assert p.answers["title"] == "Lab 4" and all(q["key"] != "title" for q in p.open_questions)


@pytest.mark.parametrize("width,style,expect", [(0.5, "single", 'w:sz="4"'), (3, "double", 'w:val="double"'), (0, "single", None)])
def test_border_options(home, monkeypatch, width, style, expect):
    monkeypatch.setenv("DOCUMENTING_MCP_REQUIRE_PLAN", "0")
    res = server.create_document(template="assignment", title="T", body_markdown="# Q\n\nA.\n",
                                 border_width_pt=width, border_style=style)
    xml = _xml(res["docx"])
    if expect is None:
        assert "pgBorders" not in xml
    else:
        assert expect in xml


def test_get_my_input_here_flow(home):
    pid = _call("start_assignment", {"request": "Lab 4 report", "template": "lab_report"})["plan_id"]
    r = server.save_plan(pid, steps=["Write", "Check"], answers={"title": "Lab 4"},
                         sections=["Aim", "Theory", "Procedure", "Result", "Discussion", "Conclusion"])
    assert "- [ ] Theory" in r["plan"] and "- [x] Result" in r["plan"] and "- [x] Discussion" in r["plan"]
    # the student ticks only Result and Conclusion
    r = server.save_plan(pid, steps=["Write", "Check"], input_sections=["Result", "Conclusion"])
    assert "- [ ] Discussion" in r["plan"] and "- [x] Conclusion" in r["plan"]
    server.approve_plan(pid, "ok")

    body = "# Aim\n\nTo test.\n\n# Result\n\nIt worked.\n\n# Conclusion\n\nDone.\n"
    blocked = server.create_document(template="lab_report", title="Lab 4", body_markdown=body, plan_id=pid)
    assert set(blocked["missing_input"]) == {"Result", "Conclusion"}

    q = server.ask_section_input(pid, "Result")
    assert any("measure" in x for x in q["questions"])
    assert "error" in server.save_section_input(pid, "Result", "  ")
    server.save_section_input(pid, "Result", "LCD showed KDU UNIVERSITY; address was 0x48; first try failed (address shifted twice)")
    server.save_section_input(pid, "4. Conclusion", "I learnt how I2C addressing works")  # numbering ignored
    res = server.create_document(template="lab_report", title="Lab 4", body_markdown=body, plan_id=pid)
    assert "error" not in res
    assert "input received" in server.get_plan(pid)["plan"]
    rep = server.check_document(res["docx"])
    assert rep["summary"]["sections_from_student_input"] == "2 of 2 ticked sections"

    # a ticked section added later without input is blocked
    server.save_plan(pid, steps=["Write", "Check"], sections=["Aim", "Result", "Conclusion", "Discussion"],
                     input_sections=["Result", "Conclusion", "Discussion"])
    out = server.insert_section(res["docx"], "# Discussion\n\nText.", before="Conclusion")
    assert out["missing_input"] == ["Discussion"]
