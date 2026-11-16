"""Єдина точка входу для вправ (використовують і UI, і tools). Модулі підключаються за назвою."""
import importlib
import uuid

import config
from db import repo
from errors import AppError

GENERATABLE = ("writing", "reading", "speaking")


def _mod(module: str):
    if module not in GENERATABLE:
        raise AppError("VALIDATION_ERROR", f"Модуль «{module}» не підтримує generate_exercise.")
    return importlib.import_module(f"modules.{module}")


def generate(student_id: str, module: str, exercise_type=None, topic=None, difficulty=None) -> dict:
    student = repo.get_student(student_id)
    mod = _mod(module)
    spec = mod.generate(student, exercise_type, topic, difficulty)
    ex = repo.create_exercise(student_id, module, spec, student["test_type"])
    return {"exercise_id": ex["id"], "module": module, "title": ex["title"],
            "estimated_minutes": ex["content_json"].get("estimated_minutes"),
            "display_markdown": mod.render_task(ex)}


def student_view(student_id: str, exercise_id: str) -> dict:
    ex = repo.get_exercise(student_id, exercise_id)
    if ex is None:
        raise AppError("NOT_FOUND", "Вправу не знайдено.")
    return {"exercise_id": ex["id"], "status": ex["status"], "display_markdown": _mod(ex["module"]).render_task(ex)}


def submit(student_id: str, exercise_id: str, answer_text: str | None = None, answers: dict | None = None,
           submission_id: str | None = None, elapsed_seconds: int | None = None) -> dict:
    ex = repo.get_exercise(student_id, exercise_id)  # ownership check
    if ex is None:
        raise AppError("NOT_FOUND", "Вправу не знайдено.")
    sid = submission_id or f"{exercise_id}"  # за замовчуванням: одна спроба на вправу
    existing = repo.get_attempt_by_submission(student_id, sid)
    if existing:
        return {"attempt_id": existing["id"], "duplicate": True, "provenance": existing["provenance"],
                "markdown": existing["evaluation_json"].get("markdown", "Результат уже збережено.")}
    if ex["status"] == "completed":
        raise AppError("CONFLICT", "Цю вправу вже завершено. Згенеруйте нову.")
    if not (answer_text or "").strip() and not answers:
        raise AppError("VALIDATION_ERROR", "Порожня відповідь.")
    mod = _mod(ex["module"])
    student = repo.get_student(student_id)
    res = mod.evaluate(ex, answer_text, answers, student)
    if res.get("insufficient"):  # занадто коротка відповідь: підказка без збереження спроби
        return {"attempt_id": None, "duplicate": False, "provenance": "unknown", "saved": False,
                "markdown": res["markdown"]}
    ev = res["evaluation"]
    attempt = repo.save_attempt(student_id, exercise_id, ex["module"], sid,
                                {"answer_text": answer_text, "answers": answers}, ev, res["provenance"],
                                res["raw"][0], res["raw"][1], elapsed_seconds,
                                ev.get("rubric_version", ""), config.PROMPT_VERSION)
    for m in res["mistakes"]:
        repo.add_mistake(student_id, attempt["id"], ex["module"], m["subskill"], m["original"],
                         m["correction"], m["explanation"])
    repo.set_exercise_status(student_id, exercise_id, "completed")
    repo.add_event(student_id, ex["module"], "attempt_submitted",
                   {"attempt_id": attempt["id"], "provenance": res["provenance"]})
    return {"attempt_id": attempt["id"], "duplicate": False, "provenance": res["provenance"],
            "markdown": res["markdown"]}
