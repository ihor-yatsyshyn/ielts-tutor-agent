import json

from agent import tools, tutor
from db import repo
from modules import listening  # noqa
from services import planner
from services.progress import get_progress
from tests.fakes import FakeLLM, tool_reply
from agent.llm import LLMReply


def test_tool_schemas_are_valid_json():
    s = tools.tool_schemas()
    assert len(s) == len(tools.TOOLS)
    json.dumps(s)


def test_executor_rejects_unknown_and_bad_args(student):
    assert tools.execute(student["id"], "drop_database", "{}")["error"]["code"] == "VALIDATION_ERROR"
    r = tools.execute(student["id"], "update_student_profile", '{"target_band": 12}')
    assert r["ok"] is False and r["error"]["code"] == "VALIDATION_ERROR"


def test_executor_uses_context_student_not_model_argument(student, student2):
    # модель може підсунути чужий student_id/exercise_id: виконується лише в межах контексту
    ex = repo.create_exercise(student["id"], "writing", {"exercise_type": "task2", "content": {}}, "Academic")
    r = tools.execute(student2["id"], "submit_answer", json.dumps({"exercise_id": ex["id"], "answer_text": "hi"}))
    assert r["ok"] is False and r["error"]["code"] == "NOT_FOUND"


def test_agent_loop_tool_then_text(student):
    llm = FakeLLM(replies=[tool_reply("get_student_profile"), LLMReply(content="Привіт! Ціль 7.0.")])
    out = tutor.handle_user_turn(student["id"], "яка в мене ціль?", llm=llm)
    assert out == "Привіт! Ціль 7.0."
    second_call = llm.chat_calls[1]["messages"]
    assert any(m["role"] == "tool" for m in second_call)          # tool result повернувся моделі
    assert len(repo.recent_messages(student["id"])) == 2          # історія збережена


def test_agent_round_limit(student):
    llm = FakeLLM(replies=[tool_reply("get_student_profile")] * 10 + [LLMReply(content="final")])
    out = tutor.handle_user_turn(student["id"], "loop", llm=llm)
    assert out  # не зависає; після ліміту викликається без tools
    assert llm.chat_calls[-1]["tools"] is None


def test_planner_deterministic_and_unknown_not_zero(student):
    a = planner.score_modules(student["id"])
    b = planner.score_modules(student["id"])
    assert a == b
    p = get_progress(student["id"])
    assert all(v["status"] == "unknown" and v["value"] is None for v in p["modules"].values())


def test_explicit_request_overrides_ranking(student):
    r = planner.get_next_activity(student["id"], preferred_module="speaking")
    assert r["module"] == "speaking"


def test_plan_versioning_via_tool(student):
    tools.execute(student["id"], "create_or_update_study_plan", "{}")
    r = tools.execute(student["id"], "create_or_update_study_plan", '{"planning_horizon_days": 28}')
    assert r["data"]["version"] == 2
