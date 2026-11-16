"""Репозиторій: єдине місце, де є SQL/ORM. Усі запити скоуплені по student_id.
Повертає прості dict (без detached-проблем)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from db.models import (Attempt, ChatMessage, Exercise, ListeningAssignment, Mistake,
                       ProgressEvent, Student, StudyPlan, ToolExecution)
from db.session import session_scope
from errors import AppError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def to_dict(o) -> dict:
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


# ---------- students ----------
PROFILE_FIELDS = {"display_name", "test_type", "target_band", "current_level", "exam_date",
                  "weekly_study_days", "minutes_per_session", "topic_preferences", "feedback_style"}


def get_or_create_student(nickname: str) -> dict:
    nickname = nickname.strip().lower()
    if not nickname or len(nickname) > 64:
        raise AppError("VALIDATION_ERROR", "Нікнейм має бути від 1 до 64 символів.")
    with session_scope() as s:
        st = s.scalar(select(Student).where(Student.nickname == nickname))
        if st is None:
            st = Student(nickname=nickname, display_name=nickname)
            s.add(st)
            s.flush()
        return to_dict(st)


def get_student(student_id: str) -> dict:
    with session_scope() as s:
        st = s.get(Student, student_id)
        if st is None:
            raise AppError("PROFILE_NOT_FOUND", "Профіль не знайдено. Пройдіть onboarding.")
        return to_dict(st)


def update_student(student_id: str, patch: dict) -> dict:
    bad = set(patch) - PROFILE_FIELDS
    if bad:
        raise AppError("VALIDATION_ERROR", f"Заборонені поля: {sorted(bad)}")
    with session_scope() as s:
        st = s.get(Student, student_id)
        if st is None:
            raise AppError("PROFILE_NOT_FOUND", "Профіль не знайдено.")
        changed_type = "test_type" in patch and patch["test_type"] != st.test_type
        for k, v in patch.items():
            setattr(st, k, v)
        st.version += 1
        if changed_type:  # старі вправи не чіпаємо, лише позначаємо план
            for p in s.scalars(select(StudyPlan).where(StudyPlan.student_id == student_id,
                                                       StudyPlan.status == "active")):
                p.status = "needs_review"
        s.flush()
        return to_dict(st)


# ---------- chat / tools log ----------
def add_message(student_id: str, role: str, content: str) -> None:
    with session_scope() as s:
        s.add(ChatMessage(student_id=student_id, role=role, content=content))


def recent_messages(student_id: str, limit: int = 12) -> list[dict]:
    with session_scope() as s:
        rows = s.scalars(select(ChatMessage).where(ChatMessage.student_id == student_id)
                         .order_by(ChatMessage.created_at.desc(), ChatMessage.id).limit(limit)).all()
        return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def log_tool(student_id, request_id, tool_name, args, result, status, duration_ms) -> None:
    with session_scope() as s:
        s.add(ToolExecution(student_id=student_id, request_id=request_id, tool_name=tool_name,
                            args_json=args, result_json=_trim(result), status=status,
                            duration_ms=duration_ms))


def _trim(obj, limit=4000):
    import json
    txt = json.dumps(obj, ensure_ascii=False, default=str)
    return obj if len(txt) <= limit else {"truncated": txt[:limit]}


# ---------- exercises / attempts ----------
def create_exercise(student_id: str, module: str, spec: dict, test_type: str) -> dict:
    with session_scope() as s:
        ex = Exercise(student_id=student_id, module=module, test_type=test_type,
                      exercise_type=spec["exercise_type"], title=spec.get("title", ""),
                      difficulty=spec.get("difficulty", "intermediate"),
                      subskill=spec.get("subskill", ""), content_json=spec["content"],
                      answer_key_json=spec.get("answer_key", {}),
                      eval_config_json=spec.get("eval_config", {}))
        s.add(ex)
        s.flush()
        return to_dict(ex)


def get_exercise(student_id: str, exercise_id: str) -> dict | None:
    """None, якщо вправи нема АБО вона належить іншому студенту."""
    with session_scope() as s:
        ex = s.get(Exercise, exercise_id)
        if ex is None or ex.student_id != student_id:
            return None
        return to_dict(ex)


def list_active_exercises(student_id: str, limit: int = 5) -> list[dict]:
    with session_scope() as s:
        rows = s.scalars(select(Exercise).where(Exercise.student_id == student_id,
                                                Exercise.status.in_(["assigned", "in_progress"]))
                         .order_by(Exercise.created_at.desc()).limit(limit)).all()
        return [to_dict(r) for r in rows]


def set_exercise_status(student_id: str, exercise_id: str, status: str) -> None:
    with session_scope() as s:
        ex = s.get(Exercise, exercise_id)
        if ex and ex.student_id == student_id:
            ex.status = status


def get_attempt_by_submission(student_id: str, submission_id: str) -> dict | None:
    with session_scope() as s:
        a = s.scalar(select(Attempt).where(Attempt.submission_id == submission_id,
                                           Attempt.student_id == student_id))
        return to_dict(a) if a else None


def save_attempt(student_id: str, exercise_id: str, module: str, submission_id: str,
                 response: dict, evaluation: dict, provenance: str,
                 raw_correct=None, raw_total=None, elapsed_seconds=None,
                 rubric_version="", prompt_version="") -> dict:
    """Ідемпотентно: той самий submission_id повертає наявну спробу."""
    existing = get_attempt_by_submission(student_id, submission_id)
    if existing:
        existing["duplicate"] = True
        return existing
    with session_scope() as s:
        a = Attempt(student_id=student_id, exercise_id=exercise_id, module=module,
                    submission_id=submission_id, response_json=response, evaluation_json=evaluation,
                    provenance=provenance, raw_correct=raw_correct, raw_total=raw_total,
                    elapsed_seconds=elapsed_seconds, rubric_version=rubric_version,
                    prompt_version=prompt_version)
        s.add(a)
        s.flush()
        d = to_dict(a)
        d["duplicate"] = False
        return d


def list_attempts(student_id: str, module: str | None = None, since_days: int | None = None,
                  limit: int | None = None) -> list[dict]:
    with session_scope() as s:
        q = select(Attempt).where(Attempt.student_id == student_id)
        if module:
            q = q.where(Attempt.module == module)
        if since_days:
            q = q.where(Attempt.submitted_at >= utcnow() - timedelta(days=since_days))
        q = q.order_by(Attempt.submitted_at.desc() if limit else Attempt.submitted_at)
        if limit:
            q = q.limit(limit)
        return [to_dict(a) for a in s.scalars(q)]


# ---------- mistakes / events ----------
def add_mistake(student_id, attempt_id, module, subskill, original, correction, explanation) -> dict:
    key = (original or "").strip().lower()[:200]
    with session_scope() as s:
        for m in s.scalars(select(Mistake).where(Mistake.student_id == student_id,
                                                 Mistake.module == module,
                                                 Mistake.subskill == subskill,
                                                 Mistake.status != "resolved")):
            if m.original.strip().lower()[:200] == key:
                m.recurrence_count += 1
                m.status = "recurring"
                m.updated_at = utcnow()
                s.flush()
                return to_dict(m)
        m = Mistake(student_id=student_id, attempt_id=attempt_id, module=module, subskill=subskill,
                    original=original, correction=correction, explanation=explanation)
        s.add(m)
        s.flush()
        return to_dict(m)


def open_mistakes(student_id: str, module: str | None = None, limit: int = 10) -> list[dict]:
    with session_scope() as s:
        q = select(Mistake).where(Mistake.student_id == student_id, Mistake.status != "resolved")
        if module:
            q = q.where(Mistake.module == module)
        q = q.order_by(Mistake.recurrence_count.desc(), Mistake.updated_at.desc()).limit(limit)
        return [to_dict(m) for m in s.scalars(q)]


def add_event(student_id, module, event_type, payload) -> None:
    with session_scope() as s:
        s.add(ProgressEvent(student_id=student_id, module=module, event_type=event_type,
                            payload_json=payload))


# ---------- plans ----------
def create_plan(student_id, test_type, target_band, horizon_days, rationale, items) -> dict:
    with session_scope() as s:
        last = s.scalar(select(func.max(StudyPlan.version)).where(StudyPlan.student_id == student_id)) or 0
        for p in s.scalars(select(StudyPlan).where(StudyPlan.student_id == student_id,
                                                   StudyPlan.status.in_(["active", "needs_review"]))):
            p.status = "superseded"  # історію не видаляємо
        plan = StudyPlan(student_id=student_id, version=last + 1, test_type=test_type,
                         target_band=target_band, horizon_days=horizon_days,
                         rationale=rationale, items_json=items)
        s.add(plan)
        s.flush()
        return to_dict(plan)


def get_active_plan(student_id: str) -> dict | None:
    with session_scope() as s:
        p = s.scalar(select(StudyPlan).where(StudyPlan.student_id == student_id,
                                             StudyPlan.status.in_(["active", "needs_review"]))
                     .order_by(StudyPlan.version.desc()))
        return to_dict(p) if p else None


# ---------- listening ----------
def create_listening_assignment(student_id, resource, goal) -> dict:
    with session_scope() as s:
        dup = s.scalar(select(ListeningAssignment).where(
            ListeningAssignment.student_id == student_id,
            ListeningAssignment.resource_id == resource["resource_id"],
            ListeningAssignment.status == "assigned"))
        if dup:  # idempotency: не дублюємо відкрите призначення
            return to_dict(dup)
        a = ListeningAssignment(student_id=student_id, resource_id=resource["resource_id"],
                                resource_snapshot_json=resource, learning_goal=goal or "")
        s.add(a)
        s.flush()
        return to_dict(a)


def get_listening_assignment(student_id: str, assignment_id: str) -> dict | None:
    with session_scope() as s:
        a = s.get(ListeningAssignment, assignment_id)
        return to_dict(a) if a and a.student_id == student_id else None


def list_listening_assignments(student_id: str, status: str | None = None) -> list[dict]:
    with session_scope() as s:
        q = select(ListeningAssignment).where(ListeningAssignment.student_id == student_id)
        if status:
            q = q.where(ListeningAssignment.status == status)
        return [to_dict(a) for a in s.scalars(q.order_by(ListeningAssignment.assigned_at))]


def complete_listening_assignment(student_id, assignment_id, correct, total, difficult,
                                  unknown_words, notes, evidence_source) -> dict:
    with session_scope() as s:
        a = s.get(ListeningAssignment, assignment_id)
        if a is None or a.student_id != student_id:
            raise AppError("NOT_FOUND", "Listening-призначення не знайдено.")
        if a.status == "completed":
            raise AppError("CONFLICT", "Результат для цього призначення вже збережено.")
        a.status, a.completed_at = "completed", utcnow()
        a.correct_count, a.total_count = correct, total
        a.difficult_json, a.unknown_words_json = difficult, unknown_words
        a.notes, a.evidence_source = notes, evidence_source
        s.flush()
        return to_dict(a)
