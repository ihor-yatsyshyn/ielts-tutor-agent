"""Rule-based адаптація: priority score (spec 8.4), next activity, версійований план."""
from datetime import datetime, timezone

import config
from db import repo
from services.progress import MODULES, module_stats

RELEVANCE = {"writing": 1.0, "reading": 1.0, "listening": 0.9, "speaking": 0.7}
EST_MIN = {"writing": 30, "reading": 20, "listening": 20, "speaking": 10}
DEFAULT_SUBSKILL = {"writing": "task_response", "reading": "locating_detail",
                    "listening": "detail_listening", "speaking": "idea_development"}


# назви вкладок UI, куди студента скеровує тьютор (кнопок у чаті немає)
TAB_NAMES = {"writing": "Writing", "reading": "Reading", "listening": "Listening", "speaking": "Speaking"}


def _days_since(dt) -> float | None:
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - repo.ensure_utc(dt)).total_seconds() / 86400


def score_modules(student_id: str, preferred: str | None = None) -> list[dict]:
    """Детерміновано: однакові дані -> однаковий результат."""
    stats = module_stats(student_id)
    mistakes = repo.open_mistakes(student_id, limit=50)
    recent = repo.list_attempts(student_id, limit=1)
    last_module = recent[0]["module"] if recent else None
    w, rows = config.PRIORITY_WEIGHTS, []
    for m in MODULES:
        st = stats[m]
        weakness = 0.5 if st["performance"] is None else 1 - min(st["performance"], 1)
        d = _days_since(st["last_practiced_at"])
        recency = 1.0 if d is None else min(d / 7, 1.0)
        repeated = min(sum(x["recurrence_count"] for x in mistakes if x["module"] == m) / 5, 1.0)
        evidence_need = 1 - min(st["scored_points"] / 5, 1.0)  # мало доказів -> потрібна діагностика
        parts = {"weakness": weakness, "target_relevance": RELEVANCE[m], "recency": recency,
                 "repeated_error": repeated, "confidence": evidence_need,
                 "preference": 1.0 if preferred == m else 0.0, "variety": 1.0 if m != last_module else 0.0}
        score = sum(w[k] * v for k, v in parts.items())
        rows.append({"module": m, "priority": round(score, 4), "parts": parts, "stats": st})
    rows.sort(key=lambda r: (-r["priority"], r["module"]))
    return rows


def _exercise_type(student: dict, module: str, n_attempts: int) -> str | None:
    if module == "writing":
        return "task2" if n_attempts % 2 == 0 else "task1"
    if module == "speaking":
        return ["part1", "part2", "part3"][n_attempts % 3]
    return None


def _reason(row: dict, target: float, subskill: str) -> str:
    st, m = row["stats"], row["module"]
    if st["attempts"] == 0:
        return f"{m.capitalize()}: ще немає даних. Коротка діагностика дасть базову точку відліку."
    bits = []
    if st["value"] is not None:
        bits.append(f"поточний показник {st['metric']}={st['value']} ({'/'.join(st['provenance'])})")
        if m == "writing":
            bits.append(f"ціль {target}")
    d = _days_since(st["last_practiced_at"])
    if d is not None and d >= 3:
        bits.append(f"остання практика {int(d)} дн. тому")
    if row["parts"]["repeated_error"] > 0:
        bits.append(f"є повторювані помилки (фокус: {subskill})")
    return f"{m.capitalize()}: " + "; ".join(bits or ["потрібна додаткова практика"]) + "."


def get_next_activity(student_id: str, preferred_module: str | None = None,
                      max_duration_minutes: int | None = None) -> dict:
    student = repo.get_student(student_id)
    pending = repo.list_active_exercises(student_id, 1)
    if pending and (not preferred_module or pending[0]["module"] == preferred_module):
        p = pending[0]
        return {"type": "continue", "exercise_id": p["id"], "module": p["module"], "title": p["title"],
                "tab": TAB_NAMES.get(p["module"], p["module"]),
                "how_to_start": (f"Перейдіть на вкладку «{TAB_NAMES.get(p['module'], p['module'])}»: "
                                 f"незавершена вправа «{p['title']}» відкриється автоматично"),
                "reason": "У вас є незавершена вправа, доведемо її до кінця."}
    rows = score_modules(student_id, preferred_module)
    if preferred_module:  # явний запит студента має пріоритет
        rows = [r for r in rows if r["module"] == preferred_module] or rows
    if max_duration_minutes:
        fit = [r for r in rows if EST_MIN[r["module"]] <= max_duration_minutes]
        rows = fit or [r for r in rows if r["module"] == "speaking"]
    top = rows[0]
    m = top["module"]
    open_m = repo.open_mistakes(student_id, m, 1)
    subskill = open_m[0]["subskill"] if open_m else DEFAULT_SUBSKILL[m]
    return {"type": "new", "module": m, "subskill": subskill,
            "exercise_type": _exercise_type(student, m, top["stats"]["attempts"]),
            "estimated_minutes": EST_MIN[m], "priority": top["priority"],
            "reason": _reason(top, student["target_band"], subskill),
            "tab": TAB_NAMES[m], "how_to_start": f"Перейдіть на вкладку «{TAB_NAMES[m]}»"}


def create_plan(student_id: str, horizon_days: int = 14, rationale: str | None = None) -> dict:
    student = repo.get_student(student_id)
    ranked = [r["module"] for r in score_modules(student_id)]
    pattern = [ranked[0], ranked[1], ranked[2], ranked[0], ranked[3], ranked[1], ranked[2]]
    days = max(1, min(student["weekly_study_days"], 7))
    items = []
    for week in range(max(1, horizon_days // 7)):
        for slot, m in enumerate(pattern[:days], 1):
            items.append({"week": week + 1, "slot": slot, "module": m, "subskill": DEFAULT_SUBSKILL[m],
                          "minutes": student["minutes_per_session"], "status": "planned"})
    text = rationale or ("Пріоритети обчислено rule-based моделою за слабкістю, давністю практики, "
                         "повторюваними помилками та кількістю доказів. Це рекомендація, не гарантія результату.")
    return repo.create_plan(student_id, student["test_type"], student["target_band"], horizon_days, text, items)
