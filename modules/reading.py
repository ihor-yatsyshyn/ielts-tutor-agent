"""Reading: генерація passage+питань з ключем і доказами; перевірка ТІЛЬКИ кодом."""
import json
import os
import re
from typing import Literal

from pydantic import BaseModel, Field

from agent.llm import get_llm
from errors import AppError
from modules.common import norm_text

MAX_Q = 8
SUBSKILL = {"tfng": "true_false_not_given", "mcq": "multiple_choice", "short": "locating_detail"}


class RQ(BaseModel):
    type: Literal["tfng", "mcq", "short"]
    prompt: str
    options: list[str] = Field(default_factory=list)
    answer: str
    accepted: list[str] = Field(default_factory=list)
    explanation: str = ""
    evidence_excerpt: str = ""


class ReadingOut(BaseModel):
    title: str
    passage: str
    questions: list[RQ]


def _valid(q: RQ, passage: str) -> bool:
    ptxt = norm_text(passage)
    ev = norm_text(q.evidence_excerpt)
    if q.type == "tfng":
        if q.answer.strip().upper() not in ("TRUE", "FALSE", "NOT GIVEN"):
            return False
        return q.answer.strip().upper() == "NOT GIVEN" or (len(ev) > 8 and ev in ptxt)
    if q.type == "mcq":
        return (len(q.options) == 4 and q.answer.strip().upper() in "ABCD" and len(q.answer.strip()) == 1
                and len(ev) > 8 and ev in ptxt)
    return (len(q.answer.split()) <= 3 and norm_text(q.answer) in ptxt and len(ev) > 8 and ev in ptxt)


def generate(student: dict, exercise_type, topic, difficulty) -> dict:
    topic = topic or (student.get("topic_preferences") or ["technology"])[0]
    sys = ("You are an IELTS Reading item writer. Write an ORIGINAL academic-style passage (250-350 words) and "
           f"{MAX_Q} questions: mix of tfng (answer TRUE/FALSE/NOT GIVEN), mcq (4 options, answer is a letter A-D) "
           "and short (answer max 3 words copied from the passage). evidence_excerpt MUST be an exact "
           "substring of the passage (empty only for NOT GIVEN). Output json only.")
    out = get_llm().json_complete(sys, f"Topic: {topic}. Level: {difficulty or 'intermediate'}. "
                                       f"Test type: {student['test_type']}.", ReadingOut, max_tokens=3500)
    good = [q for q in out.questions if _valid(q, out.passage)][:MAX_Q]
    if len(out.passage.split()) < 120 or len(good) < 4:
        raise AppError("LLM_ERROR", "Не вдалося згенерувати якісний Reading-набір.", True)
    questions, key = [], {}
    for i, q in enumerate(good, 1):
        qid = str(i)
        questions.append({"id": qid, "type": q.type, "prompt": q.prompt,
                          "options": q.options if q.type == "mcq" else []})
        key[qid] = {"answer": q.answer.strip(), "accepted": q.accepted, "explanation": q.explanation,
                    "evidence": q.evidence_excerpt, "type": q.type}
    return {"title": out.title, "exercise_type": "reading_mixed", "difficulty": difficulty or "intermediate",
            "subskill": "mixed",
            "content": {"passage": out.passage, "questions": questions, "topic": topic,
                        "estimated_minutes": 20},
            "answer_key": key, "eval_config": {"score_conversion_id": None}}


def render_task(ex: dict) -> str:
    c = ex["content_json"]
    md = [f"### {ex['title']}\n", c["passage"], "\n---\n**Питання**"]
    for q in c["questions"]:
        hint = {"tfng": "TRUE / FALSE / NOT GIVEN", "mcq": "A-D", "short": "до 3 слів з тексту"}[q["type"]]
        md.append(f"\n**{q['id']}.** {q['prompt']}  _({hint})_")
        for letter, opt in zip("ABCD", q["options"]):
            md.append(f"   - {letter}) {opt}")
    return "\n".join(md)


def _norm_answer(qtype: str, raw: str) -> str:
    s = norm_text(raw)
    if qtype == "tfng":
        s = re.sub(r"[^a-z ]", "", s)
        return {"t": "TRUE", "true": "TRUE", "f": "FALSE", "false": "FALSE", "ng": "NOT GIVEN",
                "not given": "NOT GIVEN", "notgiven": "NOT GIVEN", "n": "NOT GIVEN"}.get(s.strip(), s.upper())
    if qtype == "mcq":
        m = re.match(r"^\W*([a-d])\b", s)
        return m.group(1).upper() if m else s.upper()
    return re.sub(r"[^\w\s-]", "", s).strip()


def check(answer_key: dict, answers: dict) -> tuple[int, int, list[dict]]:
    """Детермінована перевірка. Повертає (correct, total, details)."""
    details, correct = [], 0
    for qid, k in answer_key.items():
        given = (answers or {}).get(qid, "") or ""
        ok_set = {_norm_answer(k["type"], k["answer"])} | {_norm_answer(k["type"], a) for a in k.get("accepted", [])}
        ok = bool(given.strip()) and _norm_answer(k["type"], given) in ok_set
        correct += ok
        details.append({"id": qid, "given": given, "correct": ok, "answer": k["answer"],
                        "explanation": k.get("explanation", ""), "evidence": k.get("evidence", ""),
                        "type": k["type"]})
    return correct, len(answer_key), details


def convert_band(conversion_id, correct: int, total: int):
    """Band лише за наявної версіонованої таблиці data/score_conversion/<id>.json. Для згенерованих: None."""
    if not conversion_id:
        return None
    path = os.path.join("data", "score_conversion", f"{conversion_id}.json")
    if not os.path.exists(path):
        return None
    table = json.load(open(path, encoding="utf-8"))
    return table.get(str(correct)) if total == table.get("_total") else None


def evaluate(exercise: dict, answer_text, answers, student: dict) -> dict:
    correct, total, det = check(exercise["answer_key_json"], answers or {})
    band = convert_band(exercise["eval_config_json"].get("score_conversion_id"), correct, total)
    md = [f"### Результат: **{correct}/{total}** ({round(100 * correct / total)}%)",
          "_Перевірено автоматично за ключем (verified)._ "
          + ("" if band else "IELTS band не показано: немає каліброваної таблиці конвертації для цього тексту.")]
    mistakes = []
    for d in det:
        if d["correct"]:
            continue
        md.append(f"\n**Q{d['id']}**: ваша: `{d['given'] or '-'}` · правильна: **{d['answer']}**\n"
                  f"> {d['explanation']}" + (f"\n> _{d['evidence']}_" if d["evidence"] else ""))
        mistakes.append({"subskill": SUBSKILL[d["type"]], "original": f"Q{d['id']}: {d['given'] or '-'}",
                         "correction": d["answer"], "explanation": d["explanation"]})
    ev = {"module": "reading", "correct": correct, "total": total, "accuracy": correct / total,
          "band": band, "details": det, "is_official_score": False, "markdown": "\n".join(md)}
    return {"evaluation": ev, "mistakes": mistakes, "provenance": "verified_deterministic",
            "raw": (correct, total), "markdown": ev["markdown"]}
