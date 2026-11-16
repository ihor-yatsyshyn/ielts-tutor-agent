"""Агрегація прогресу. Лічимо в Python, не в LLM. Завжди вказуємо provenance."""
from db import repo

MODULES = ("speaking", "writing", "reading", "listening")
MIN_POINTS = 3
MISTAKE_MODULES = ("writing", "speaking")  # помилки яких модулів показуємо в «Повторюваних помилках»


def _trend(perfs: list[float]) -> str:
    if len(perfs) < 4:
        return "insufficient_data"
    h = len(perfs) // 2
    d = sum(perfs[h:]) / len(perfs[h:]) - sum(perfs[:h]) / len(perfs[:h])
    return "improving" if d > 0.05 else "declining" if d < -0.05 else "stable"


def module_stats(student_id: str, period_days: int | None = None) -> dict:
    student = repo.get_student(student_id)
    target = student["target_band"] or 7.0
    attempts = repo.list_attempts(student_id, since_days=period_days)
    listening = [a for a in repo.list_listening_assignments(student_id, "completed")]
    stats = {}
    for m in MODULES:
        pts, last, n_attempts, sources = [], None, 0, set()
        if m == "listening":
            n_attempts = len(listening)
            for a in listening:
                last = max(filter(None, [last, repo.ensure_utc(a["completed_at"])]), default=None)
                if a["total_count"]:
                    pts.append((a["correct_count"] / a["total_count"], a["correct_count"] / a["total_count"]))
                    sources.add(a["evidence_source"])
        else:
            for a in (x for x in attempts if x["module"] == m):
                n_attempts += 1
                last = max(filter(None, [last, repo.ensure_utc(a["submitted_at"])]), default=None)
                ev = a["evaluation_json"] or {}
                if m == "writing" and ev.get("overall_band") is not None:
                    pts.append((ev["overall_band"], min(ev["overall_band"] / target, 1)))
                    sources.add(a["provenance"])
                elif m == "reading" and a["raw_total"]:
                    pts.append((a["raw_correct"] / a["raw_total"], a["raw_correct"] / a["raw_total"]))
                    sources.add(a["provenance"])
                elif m == "speaking" and ev.get("level_score") is not None:
                    pts.append((ev["level_score"], ev["level_score"]))
                    sources.add(a["provenance"])
        value = sum(p[0] for p in pts) / len(pts) if pts else None
        perf = sum(p[1] for p in pts) / len(pts) if pts else None
        status = "unknown" if n_attempts == 0 else "insufficient_data" if len(pts) < MIN_POINTS else "ok"
        stats[m] = {"attempts": n_attempts, "scored_points": len(pts), "last_practiced_at": last,
                    "metric": {"writing": "estimated_band", "reading": "raw_accuracy",
                               "listening": "self_reported_accuracy", "speaking": "text_level_0_1"}[m],
                    "value": round(value, 2) if value is not None else None,
                    "performance": perf, "provenance": sorted(sources) or ["none"],
                    "trend": _trend([p[1] for p in pts]), "status": status}
    return stats


def get_progress(student_id: str, period_days: int | None = 90) -> dict:
    stats = module_stats(student_id, period_days)
    attempts = repo.list_attempts(student_id, since_days=period_days)
    minutes = round(sum((a["elapsed_seconds"] or 0) for a in attempts) / 60)
    mistakes = repo.open_mistakes(student_id, limit=8, modules=MISTAKE_MODULES)  # лише Writing і Speaking
    return {"modules": {m: {**v, "last_practiced_at": str(v["last_practiced_at"] or "")} for m, v in stats.items()},
            "total_attempts": sum(v["attempts"] for v in stats.values()), "practice_minutes": minutes,
            "open_mistakes": [{"module": x["module"], "subskill": x["subskill"], "original": x["original"][:80],
                               "correction": x["correction"][:80], "times": x["recurrence_count"],
                               "status": x["status"]} for x in mistakes],
            "note": "Writing band: неофіційна оцінка моделі; Reading: перевірено кодом; "
                    "Listening: self-reported; Speaking: лише текстова практика."}
