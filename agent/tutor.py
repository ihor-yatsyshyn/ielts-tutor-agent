"""Головний агент: один координатор, власний невеликий tool-calling цикл."""
import json
import logging
import uuid

import config
from agent import tools
from agent.llm import LLM, get_llm
from agent.prompts import SYSTEM_PROMPT
from db import repo
from errors import AppError, LLMError

log = logging.getLogger(__name__)
MAX_TOOL_CHARS = 6000


def build_context(student_id: str) -> str:
    from services.progress import get_progress
    s = repo.get_student(student_id)
    prog = get_progress(student_id, 90)
    lines = [f"STUDENT: {s['display_name']} | {s['test_type']} | target band {s['target_band']} | "
             f"level {s['current_level']} | exam {s['exam_date'] or 'n/a'} | "
             f"{s['weekly_study_days']} days/week x {s['minutes_per_session']} min | feedback {s['feedback_style']} | "
             f"topics {', '.join(s['topic_preferences'] or []) or 'n/a'}",
             "PROGRESS (from DB; provenance in brackets):"]
    for m, v in prog["modules"].items():
        lines.append(f"- {m}: {v['status']}, attempts={v['attempts']}, {v['metric']}={v['value']} "
                     f"[{'/'.join(v['provenance'])}], trend={v['trend']}")
    if prog["open_mistakes"]:
        lines.append("OPEN MISTAKES: " + "; ".join(f"{m['module']}/{m['subskill']} x{m['times']}"
                                                   for m in prog["open_mistakes"][:5]))
    pend = repo.list_active_exercises(student_id, 3)
    if pend:
        lines.append("PENDING EXERCISES (use these ids for submit_answer): " +
                     "; ".join(f"{p['id']} [{p['module']}] {p['title']}" for p in pend))
    return "\n".join(lines)


def _assistant_msg(reply) -> dict:
    return {"role": "assistant", "content": reply.content or "",
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.name, "arguments": c.arguments}} for c in reply.tool_calls]}


def handle_user_turn(student_id: str, message: str, llm: LLM | None = None) -> str:
    message = (message or "").strip()
    if not message:
        raise AppError("VALIDATION_ERROR", "Порожнє повідомлення.")
    repo.get_student(student_id)  # PROFILE_NOT_FOUND якщо нема
    llm = llm or get_llm()
    request_id = str(uuid.uuid4())
    history = repo.recent_messages(student_id, 10)
    repo.add_message(student_id, "user", message[:6000])
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + build_context(student_id)},
                *history, {"role": "user", "content": message[:6000]}]
    schemas = tools.tool_schemas()
    final = ""
    for rnd in range(config.AGENT_MAX_TOOL_ROUNDS + 1):
        use_tools = schemas if rnd < config.AGENT_MAX_TOOL_ROUNDS else None
        try:
            reply = llm.chat(messages, tools=use_tools)
        except LLMError as e:
            if use_tools and e.code == "LLM_ERROR":  # напр. malformed tool call від моделі -> відповідь без tools
                reply = llm.chat(messages, tools=None)
            else:
                raise
        if not reply.tool_calls:
            final = reply.content
            break
        messages.append(_assistant_msg(reply))
        for call in reply.tool_calls:
            res = tools.execute(student_id, call.name, call.arguments, request_id)
            payload = json.dumps(res, ensure_ascii=False, default=str)[:MAX_TOOL_CHARS]
            messages.append({"role": "tool", "tool_call_id": call.id, "content": payload})
    if not final.strip():
        final = "Я зібрав потрібні дані, але не зміг сформулювати відповідь. Уточніть, будь ласка, що саме зробити далі?"
    repo.add_message(student_id, "assistant", final)
    log.info("turn done request=%s rounds=%s prompt=%s", request_id, rnd, config.PROMPT_VERSION)
    return final
