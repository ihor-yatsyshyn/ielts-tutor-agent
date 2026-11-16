"""Реєстр tools: Pydantic-схеми, allowlist, авторизація (student_id береться з контексту, не від моделі)."""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from db import repo
from errors import AppError

log = logging.getLogger(__name__)
Module = Literal["speaking", "writing", "reading", "listening"]


class NoArgs(BaseModel):
    pass


class ProgressArgs(BaseModel):
    period_days: int = Field(90, ge=1, le=365)


class HistoryArgs(BaseModel):
    limit: int = Field(10, ge=1, le=50)
    module: Optional[Module] = None


class UpdateProfileArgs(BaseModel):
    display_name: Optional[str] = Field(None, max_length=80)
    test_type: Optional[Literal["Academic", "General Training"]] = None
    target_band: Optional[float] = Field(None, ge=4.0, le=9.0)
    current_level: Optional[Literal["A2", "B1", "B2", "C1", "unknown"]] = None
    exam_date: Optional[str] = Field(None, max_length=20)
    weekly_study_days: Optional[int] = Field(None, ge=1, le=7)
    minutes_per_session: Optional[int] = Field(None, ge=10, le=180)
    topic_preferences: Optional[list[str]] = Field(None, max_length=10)
    feedback_style: Optional[Literal["concise", "detailed"]] = None

    @field_validator("target_band")
    @classmethod
    def half_steps(cls, v):
        if v is not None and (v * 2) % 1 != 0:
            raise ValueError("target_band must be in 0.5 steps")
        return v


class NextActivityArgs(BaseModel):
    preferred_module: Optional[Module] = None
    max_duration_minutes: Optional[int] = Field(None, ge=5, le=180)


class StudyPlanArgs(BaseModel):
    planning_horizon_days: Literal[14, 28] = 14
    rationale: Optional[str] = Field(None, max_length=500)


class GenerateExerciseArgs(BaseModel):
    module: Literal["writing", "reading", "speaking"]
    exercise_type: Optional[str] = Field(None, description="writing: task1|task2; speaking: part1|part2|part3")
    topic: Optional[str] = Field(None, max_length=60)
    difficulty: Optional[Literal["beginner", "intermediate", "upper_intermediate", "advanced"]] = None


class SubmitAnswerArgs(BaseModel):
    exercise_id: str
    answer_text: Optional[str] = Field(None, max_length=8000, description="essay / speaking text")
    answers: Optional[dict[str, str]] = Field(None, description='reading: {"1":"TRUE","2":"B"}')


class ListeningResArgs(BaseModel):
    level: Optional[Literal["A1", "A2", "B1", "B2", "C1", "C2"]] = None
    topic: Optional[str] = Field(None, max_length=40)
    limit: int = Field(3, ge=1, le=10)


class AssignListeningArgs(BaseModel):
    resource_id: str
    learning_goal: Optional[str] = Field(None, max_length=300)


class SubmitListeningArgs(BaseModel):
    assignment_id: str
    correct_count: Optional[int] = Field(None, ge=0)
    total_count: Optional[int] = Field(None, gt=0)
    difficult_questions: Optional[list[str]] = Field(None, max_length=30)
    unknown_words: Optional[list[str]] = Field(None, max_length=30)
    notes: Optional[str] = Field(None, max_length=1000)


# ---------------- handlers: (student_id, args) -> dict ----------------
def _profile(sid, a):
    s = repo.get_student(sid)
    return {k: s[k] for k in ("display_name", "test_type", "target_band", "current_level", "exam_date",
                              "weekly_study_days", "minutes_per_session", "topic_preferences", "feedback_style")}


def _update_profile(sid, a: UpdateProfileArgs):
    patch = a.model_dump(exclude_none=True)
    if not patch:
        raise AppError("VALIDATION_ERROR", "Немає полів для оновлення.")
    st = repo.update_student(sid, patch)
    return {"updated": sorted(patch), "profile_version": st["version"],
            "plan_recalculation_recommended": "test_type" in patch or "target_band" in patch}


def _progress(sid, a: ProgressArgs):
    from services.progress import get_progress
    return get_progress(sid, a.period_days)


def _history(sid, a: HistoryArgs):
    items = repo.list_attempts(sid, a.module, limit=a.limit)
    return {"items": [{"module": x["module"], "date": str(x["submitted_at"])[:10], "provenance": x["provenance"],
                       "score": (f"{x['raw_correct']}/{x['raw_total']}" if x["raw_total"] else
                                 x["evaluation_json"].get("overall_band"))} for x in items]}


def _next(sid, a: NextActivityArgs):
    from services.planner import get_next_activity
    return get_next_activity(sid, a.preferred_module, a.max_duration_minutes)


def _plan(sid, a: StudyPlanArgs):
    from services.planner import create_plan
    p = create_plan(sid, a.planning_horizon_days, a.rationale)
    return {"plan_id": p["id"], "version": p["version"], "items": p["items_json"][:14], "rationale": p["rationale"]}


def _generate(sid, a: GenerateExerciseArgs):
    from services import exercises
    return exercises.generate(sid, a.module, a.exercise_type, a.topic, a.difficulty)


def _submit(sid, a: SubmitAnswerArgs):
    from services import exercises
    r = exercises.submit(sid, a.exercise_id, a.answer_text, a.answers)
    return {"attempt_id": r["attempt_id"], "provenance": r["provenance"], "display_markdown": r["markdown"]}


def _listening_search(sid, a: ListeningResArgs):
    from modules import listening
    s = repo.get_student(sid)
    return {"resources": listening.search(a.level or (s["current_level"] if s["current_level"] != "unknown" else None),
                                          a.topic, a.limit)}


def _listening_assign(sid, a: AssignListeningArgs):
    from modules import listening
    return listening.assign(sid, a.resource_id, a.learning_goal)


def _listening_submit(sid, a: SubmitListeningArgs):
    from modules import listening
    r = listening.submit(sid, a.assignment_id, a.correct_count, a.total_count, a.difficult_questions,
                         a.unknown_words, a.notes or "")
    return {"score_status": r["evaluation"]["score_status"], "display_markdown": r["display_markdown"]}


TOOLS: dict[str, tuple[type[BaseModel], Callable, str]] = {
    "get_student_profile": (NoArgs, _profile, "Get the student's saved profile and study settings."),
    "update_student_profile": (UpdateProfileArgs, _update_profile, "Update allowed profile fields (goal, test type, schedule)."),
    "get_student_progress": (ProgressArgs, _progress, "Get aggregated progress per module with score provenance and open mistakes."),
    "get_learning_history": (HistoryArgs, _history, "Get recent attempts (module, date, score, provenance)."),
    "get_next_activity": (NextActivityArgs, _next, "Recommend the next activity with a data-based reason."),
    "create_or_update_study_plan": (StudyPlanArgs, _plan, "Create a new versioned study plan (14 or 28 days)."),
    "generate_exercise": (GenerateExerciseArgs, _generate, "Create a Writing/Reading/Speaking exercise. Show display_markdown verbatim."),
    "submit_answer": (SubmitAnswerArgs, _submit, "Evaluate and save the student's answer to a pending exercise. Show display_markdown verbatim."),
    "get_listening_resources": (ListeningResArgs, _listening_search, "Find curated EXTERNAL listening resources."),
    "assign_listening_exercise": (AssignListeningArgs, _listening_assign, "Assign an external listening resource to the student."),
    "submit_listening_results": (SubmitListeningArgs, _listening_submit, "Save the student's self-reported listening result."),
}


def _simplify(node):
    """Прибираємо anyOf-null/title, щоб схема була простою для tool calling у Llama."""
    if isinstance(node, dict):
        if "anyOf" in node:
            non_null = [x for x in node["anyOf"] if x.get("type") != "null"]
            if len(non_null) == 1:
                extra = {k: v for k, v in node.items() if k not in ("anyOf", "default")}
                return _simplify({**non_null[0], **extra})
        return {k: _simplify(v) for k, v in node.items() if k not in ("title", "default")}
    if isinstance(node, list):
        return [_simplify(x) for x in node]
    return node


def tool_schemas() -> list[dict]:
    out = []
    for name, (model, _, desc) in TOOLS.items():
        params = _simplify(model.model_json_schema())
        params.setdefault("properties", {})
        out.append({"type": "function", "function": {"name": name, "description": desc, "parameters": params}})
    return out


def execute(student_id: str, name: str, raw_args: str, request_id: str | None = None) -> dict:
    """Allowlist -> JSON parse -> Pydantic -> виконання -> лог. student_id завжди з контексту."""
    request_id = request_id or str(uuid.uuid4())
    t0, args = time.time(), {}
    try:
        if name not in TOOLS:
            raise AppError("VALIDATION_ERROR", f"Невідомий tool: {name}")
        model, handler, _ = TOOLS[name]
        try:
            args = json.loads(raw_args) if (raw_args or "").strip() else {}
            if not isinstance(args, dict):
                raise ValueError
            parsed = model.model_validate(args)
        except (ValueError, ValidationError) as e:
            raise AppError("VALIDATION_ERROR", f"Некоректні аргументи: {str(e)[:300]}")
        data = handler(student_id, parsed)
        result = {"ok": True, "data": data, "meta": {"request_id": request_id}, "error": None}
    except AppError as e:
        result = {"ok": False, "data": None, "meta": {"request_id": request_id},
                  "error": {"code": e.code, "message": e.message, "retryable": e.retryable}}
    except Exception as e:  # noqa
        log.exception("Tool %s failed (request %s)", name, request_id)
        result = {"ok": False, "data": None, "meta": {"request_id": request_id},
                  "error": {"code": "INTERNAL_ERROR", "message": "Внутрішня помилка інструмента.", "retryable": False}}
    repo.log_tool(student_id, request_id, name, args if isinstance(args, dict) else {}, result,
                  "ok" if result["ok"] else "error", int((time.time() - t0) * 1000))
    return result
