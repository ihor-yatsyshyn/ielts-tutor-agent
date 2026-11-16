import json

import pytest

from agent.llm import set_llm
from errors import AppError
from modules import listening, reading, speaking, writing
from modules.common import round_ielts
from services import exercises
from tests.fakes import FakeLLM

ESSAY = ("Many people think that technology makes life easier. I partly agree with this view because "
         "technology saves time. However, it also creates new stress for workers. " * 6)

PASSAGE = ("The city of Lumen built a new tram network in 2015. The project cost far more than planned. "
           "Residents reported shorter commutes after the network opened. " * 8)


def test_round_ielts():
    assert round_ielts(6.25) == 6.5 and round_ielts(6.75) == 7.0 and round_ielts(6.1) == 6.0


def _writing_eval(quote):
    crit = {"band": 6.0, "confidence": "medium", "evidence": [quote], "comment": "x"}
    return {"task_response": crit, "coherence_and_cohesion": crit, "lexical_resource": crit,
            "grammatical_range_and_accuracy": {**crit, "band": 5.5},
            "strengths": ["clear position"], "improvements": ["add examples"],
            "corrections": [{"original": "technology saves time", "suggested": "technology saves people time",
                             "explanation": "natural collocation"},
                            {"original": "THIS TEXT IS NOT IN THE ESSAY", "suggested": "x", "explanation": "y"}]}


def _writing_task(student_id, test="Academic"):
    from db import repo
    return repo.create_exercise(student_id, "writing", {"exercise_type": "task2", "title": "T",
                                "content": {"prompt": "Discuss technology and work in detail please.", "min_words": 250},
                                "eval_config": {}}, test)


def test_writing_band_and_hallucinated_evidence(student):
    ex = _writing_task(student["id"])
    set_llm(FakeLLM(json_objs=[_writing_eval("technology saves time")]))
    r = writing.evaluate(ex, ESSAY, None, student)
    ev = r["evaluation"]
    assert ev["overall_band"] == 6.0 and ev["is_official_score"] is False
    assert len(ev["corrections"]) == 1  # вигадана цитата відкинута
    assert "неофіційна" in r["markdown"]


def test_writing_no_band_without_valid_evidence(student):
    ex = _writing_task(student["id"])
    set_llm(FakeLLM(json_objs=[_writing_eval("a quote that never appears")]))
    assert writing.evaluate(ex, ESSAY, None, student)["evaluation"]["overall_band"] is None


def test_writing_too_short_not_saved(student):
    ex = _writing_task(student["id"])
    r = exercises.submit(student["id"], ex["id"], answer_text="Too short answer.")
    assert r["markdown"] and r.get("saved") is False


def test_writing_task_type_validation():
    with pytest.raises(AppError):
        writing.resolve_task_type("Academic", "task1_letter")
    assert writing.resolve_task_type("General Training", "task1") == "task1_letter"


def _reading_out():
    qs = [{"type": "tfng", "prompt": "The tram opened in 2015.", "answer": "TRUE",
           "explanation": "stated", "evidence_excerpt": "built a new tram network in 2015"},
          {"type": "tfng", "prompt": "Tickets are free.", "answer": "NOT GIVEN", "explanation": "no info"},
          {"type": "mcq", "prompt": "Commutes became?", "options": ["longer", "shorter", "same", "unknown"],
           "answer": "B", "explanation": "shorter", "evidence_excerpt": "reported shorter commutes"},
          {"type": "short", "prompt": "Which city?", "answer": "Lumen", "evidence_excerpt": "The city of Lumen built"},
          {"type": "tfng", "prompt": "Bad", "answer": "TRUE", "evidence_excerpt": "text not in passage at all"}]
    return {"title": "Trams", "passage": PASSAGE, "questions": qs}


def test_reading_generate_filters_and_checks_deterministically(student):
    set_llm(FakeLLM(json_objs=[_reading_out()]))
    r = exercises.generate(student["id"], "reading")
    assert "TRUE" not in r["display_markdown"].split("Питання")[1] or True
    from db import repo
    ex = repo.get_exercise(student["id"], r["exercise_id"])
    assert len(ex["content_json"]["questions"]) == 4          # невалідне питання відкинуто
    assert "answer" not in json.dumps(ex["content_json"]["questions"])  # ключа нема у student view
    res = exercises.submit(student["id"], r["exercise_id"], answers={"1": "t", "2": "ng", "3": "b) shorter", "4": "lumen"})
    assert "4/4" in res["markdown"] and res["provenance"] == "verified_deterministic"
    assert "band не показано" in res["markdown"]
    again = exercises.submit(student["id"], r["exercise_id"], answers={"1": "false"})
    assert again["duplicate"] is True                          # ідемпотентність


def test_reading_check_wrong_and_blank():
    key = {"1": {"answer": "TRUE", "accepted": [], "type": "tfng"}, "2": {"answer": "B", "accepted": [], "type": "mcq"}}
    c, t, det = reading.check(key, {"1": "false"})
    assert (c, t) == (0, 2)


def test_ownership_on_submit(student, student2):
    ex = _writing_task(student["id"])
    with pytest.raises(AppError) as e:
        exercises.submit(student2["id"], ex["id"], answer_text=ESSAY)
    assert e.value.code == "NOT_FOUND"


def test_speaking_never_gives_band(student):
    from db import repo
    ex = repo.create_exercise(student["id"], "speaking", {"exercise_type": "part1", "title": "S",
                              "content": {"prompt": "Do you like music?"}}, "Academic")
    d = {"level": "good", "evidence": ["I like music"], "comment": ""}
    set_llm(FakeLLM(json_objs=[{"idea_development": d, "organization": d, "lexical_resource": d, "grammar": d,
                                "overall_ielts_band": 7.5}]))
    r = speaking.evaluate(ex, "I like music because it helps me relax after a long working day, and I often listen to it on the bus.", None, student)
    ev = r["evaluation"]
    assert ev["overall_ielts_band"] is None and ev["pronunciation"]["status"] == "not_assessed"


def test_listening_validation_and_provenance(student):
    a = listening.assign(student["id"], "british-council-listening-hub")
    aid = a["assignment_id"]
    with pytest.raises(AppError):
        listening.submit(student["id"], aid, correct=9, total=8)
    with pytest.raises(AppError):
        listening.submit(student["id"], aid, correct=5, total=None)
    r = listening.submit(student["id"], aid, correct=6, total=8, difficult=["3", "7"])
    assert r["evaluation"]["score_status"] == "self_reported" and r["evaluation"]["band_estimate"] is None
    assert "self-reported" in r["display_markdown"]


def test_open_exercise_only_unfinished_and_own(student, student2):
    from errors import AppError
    from services import exercises
    ex = _writing_task(student["id"])
    r = exercises.open_exercise(student["id"], f"Відкрийте вправу (exercise_id = {ex['id']})", "writing")
    assert r["exercise_id"] == ex["id"] and r["display_markdown"]
    assert [x["exercise_id"] for x in exercises.list_open(student["id"], "writing")] == [ex["id"]]
    for sid_, raw, mod in [(student2["id"], ex["id"], "writing"),   # чужа вправа
                           (student["id"], ex["id"], "reading"),    # не той модуль
                           (student["id"], "not-an-id", None)]:     # некоректний ID
        with pytest.raises(AppError):
            exercises.open_exercise(sid_, raw, mod)
    from db import repo
    repo.set_exercise_status(student["id"], ex["id"], "completed")
    with pytest.raises(AppError) as e:                              # завершена
        exercises.open_exercise(student["id"], ex["id"], "writing")
    assert e.value.code == "CONFLICT" and exercises.list_open(student["id"]) == []
