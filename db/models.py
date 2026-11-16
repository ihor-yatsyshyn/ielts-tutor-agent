from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Student(Base):
    """Student + StudentProfile в одній таблиці (MVP)."""
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    nickname: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80), default="")
    test_type: Mapped[str] = mapped_column(String(20), default="Academic")  # Academic | General Training
    target_band: Mapped[float] = mapped_column(Float, default=7.0)
    current_level: Mapped[str] = mapped_column(String(20), default="unknown")
    exam_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weekly_study_days: Mapped[int] = mapped_column(Integer, default=4)
    minutes_per_session: Mapped[int] = mapped_column(Integer, default=30)
    topic_preferences: Mapped[list] = mapped_column(JSON, default=list)
    feedback_style: Mapped[str] = mapped_column(String(20), default="detailed")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | superseded | needs_review
    test_type: Mapped[str] = mapped_column(String(20), default="Academic")
    target_band: Mapped[float] = mapped_column(Float, default=7.0)
    horizon_days: Mapped[int] = mapped_column(Integer, default=14)
    rationale: Mapped[str] = mapped_column(Text, default="")
    items_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Exercise(Base):
    __tablename__ = "exercises"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    module: Mapped[str] = mapped_column(String(20))
    exercise_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200), default="")
    difficulty: Mapped[str] = mapped_column(String(30), default="intermediate")
    subskill: Mapped[str] = mapped_column(String(60), default="")
    test_type: Mapped[str] = mapped_column(String(20), default="Academic")
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    answer_key_json: Mapped[dict] = mapped_column(JSON, default=dict)  # НІКОЛИ не віддавати в student view
    eval_config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="assigned")  # assigned|in_progress|completed|abandoned
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Attempt(Base):
    """ExerciseAttempt + Evaluation разом (MVP)."""
    __tablename__ = "attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)
    module: Mapped[str] = mapped_column(String(20), index=True)
    submission_id: Mapped[str] = mapped_column(String(80), unique=True)  # idempotency key
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[str] = mapped_column(String(30), default="unknown")
    raw_correct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rubric_version: Mapped[str] = mapped_column(String(40), default="")
    prompt_version: Mapped[str] = mapped_column(String(40), default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Mistake(Base):
    __tablename__ = "mistakes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    module: Mapped[str] = mapped_column(String(20))
    subskill: Mapped[str] = mapped_column(String(60), default="")
    original: Mapped[str] = mapped_column(Text, default="")
    correction: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="new")  # new|recurring|practising|resolved
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    tool_name: Mapped[str] = mapped_column(String(60))
    args_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ListeningAssignment(Base):
    """ListeningAssignment + ListeningResult разом (MVP)."""
    __tablename__ = "listening_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    resource_id: Mapped[str] = mapped_column(String(80))
    resource_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    learning_goal: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="assigned")  # assigned | completed
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficult_json: Mapped[list] = mapped_column(JSON, default=list)
    unknown_words_json: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_source: Mapped[str] = mapped_column(String(30), default="self_reported")


class ProgressEvent(Base):
    __tablename__ = "progress_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    module: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(40))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
