"""Listening: зовнішні ресурси + звіт студента. Жодного аудіо в застосунку."""
import json
import os
from urllib.parse import urlparse

from db import repo
from errors import AppError

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "listening_resources.json")
CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"]


def load_catalog() -> list[dict]:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        items = json.load(f)
    return [r for r in items if r.get("status") == "active"
            and urlparse(r["url"]).scheme == "https"]  # лише активні HTTPS


def _level_range(s: str) -> tuple[int, int]:
    lo, _, hi = s.partition("-")
    return CEFR.index(lo.strip()), CEFR.index((hi or lo).strip())


def search(level: str | None = None, topic: str | None = None, limit: int = 3) -> list[dict]:
    res = []
    for r in load_catalog():
        score = 0
        if level in CEFR:
            lo, hi = _level_range(r["level"])
            score += 2 if lo <= CEFR.index(level) <= hi else 0
        if topic and topic.lower() in [t.lower() for t in r.get("topics", [])]:
            score += 1
        score += {"official": 1, "IELTS-style": 0.5}.get(r.get("ielts_relevance"), 0)
        res.append((score, r))
    res.sort(key=lambda x: -x[0])
    return [r for _, r in res[:max(1, min(limit, 10))]]


def get_resource(resource_id: str) -> dict:
    for r in load_catalog():
        if r["resource_id"] == resource_id:
            return r
    raise AppError("NOT_FOUND", "Ресурс не знайдено або вимкнений.")


def assign(student_id: str, resource_id: str, goal: str | None = None) -> dict:
    r = get_resource(resource_id)
    a = repo.create_listening_assignment(student_id, r, goal)
    return {"assignment_id": a["id"], "resource": r, "status": a["status"],
            "display_markdown": (f"### {r['title']} ({r['provider']})\n"
                                 f"1. Відкрийте посилання: **{r['url']}**\n2. Прослухайте і виконайте вправу на сайті.\n"
                                 "3. Поверніться сюди й внесіть результат (скільки правильних / скільки всього, "
                                 "які питання були складні, незнайомі слова).\n\n"
                                 f"_{r.get('usage_notes', '')}_  \n_Аудіо в цьому застосунку не відтворюється._")}


def submit(student_id: str, assignment_id: str, correct=None, total=None, difficult=None,
           unknown_words=None, notes: str = "") -> dict:
    a = repo.get_listening_assignment(student_id, assignment_id)
    if a is None:
        raise AppError("NOT_FOUND", "Призначення не знайдено.")
    if (correct is None) != (total is None):
        raise AppError("VALIDATION_ERROR", "Вкажіть обидва числа (правильних і всього) або жодного.")
    if correct is not None and (total <= 0 or correct < 0 or correct > total):
        raise AppError("VALIDATION_ERROR", "Має виконуватись 0 ≤ правильних ≤ всього, всього > 0.")
    clean = lambda xs: [str(x).strip()[:60] for x in (xs or []) if str(x).strip()][:30]
    row = repo.complete_listening_assignment(student_id, assignment_id, correct, total, clean(difficult),
                                             clean(unknown_words), (notes or "")[:1000], "self_reported")
    repo.add_event(student_id, "listening", "listening_result",
                   {"assignment_id": assignment_id, "correct": correct, "total": total, "source": "self_reported"})
    return {"result": row, "evaluation": evaluate(row), "display_markdown": evaluate(row)["markdown"]}


def evaluate(row: dict) -> dict:
    c, t = row.get("correct_count"), row.get("total_count")
    md = ["### Listening: підсумок"]
    if c is None:
        md.append("Ви не вказали рахунок, тому числової оцінки немає (score = null).")
        acc = None
    else:
        acc = c / t
        md.append(f"За **вашим звітом**: {c}/{t} ({round(acc * 100)}%). "
                  "Я не перевіряв ключ провайдера, тож це **self-reported** результат; IELTS band не обчислюється.")
    if row.get("difficult_json"):
        md.append(f"Складні питання: {', '.join(row['difficult_json'])}. Що саме ускладнило: лексика, швидкість, "
                  "перефразування, відволікання? (це ваша рефлексія, не встановлений факт)")
    if row.get("unknown_words_json"):
        md.append(f"Нові слова для повторення: {', '.join(row['unknown_words_json'])}.")
    return {"score_status": "self_reported", "accuracy": acc, "band_estimate": None, "markdown": "\n\n".join(md)}
