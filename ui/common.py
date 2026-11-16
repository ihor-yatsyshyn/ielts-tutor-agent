import functools
import logging

import gradio as gr

from errors import AppError

log = logging.getLogger(__name__)


def guard(fn):
    """Перетворює помилки застосунку на дружній gr.Error (toast), без stack trace."""
    @functools.wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except gr.Error:
            raise
        except AppError as e:
            raise gr.Error(e.message + (" Спробуйте ще раз." if e.retryable else ""))
        except Exception:
            log.exception("Unhandled UI error")
            raise gr.Error("Внутрішня помилка. Спробуйте ще раз.")
    return wrapper


def need_sid(sid: str) -> str:
    if not sid:
        raise gr.Error("Спочатку створіть профіль на вкладці «Профіль».")
    return sid


def section_header(title: str, subtitle: str = "", sub: bool = False, level: int = 2) -> gr.HTML:
    """Центрований заголовок розділу (підзаголовок може містити <b>...</b>)."""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    cls = "section-head sub" if sub else "section-head"
    return gr.HTML(f'<div class="{cls}"><h{level}>{title}</h{level}>{sub_html}</div>')


def open_by_id_widgets(sid: gr.State, module: str):
    """Блок «Відкрити незавершену вправу»: список незавершених вправ модуля або вставлений ID.
    Повертає (dropdown, кнопка); підключення обробника робить вкладка."""
    from services import exercises

    with gr.Accordion("Відкрити незавершену вправу за ID", open=False, elem_classes="narrow") as acc:
        pick = gr.Dropdown([], value=None, allow_custom_value=True,
                           label="Незавершена вправа (оберіть зі списку або вставте ID)")
        btn = gr.Button("Відкрити вправу", variant="secondary", elem_classes="cta")

    def refresh(sid_):
        if not sid_:
            return gr.update(choices=[])
        return gr.update(choices=[(f"{r['title'] or 'Вправа'} ({r['exercise_id'][:8]})", r["exercise_id"])
                                  for r in exercises.list_open(sid_, module)])

    acc.expand(refresh, sid, pick)
    pick.focus(refresh, sid, pick)
    return pick, btn


def resume_on_select(tab, sid: gr.State, ex_id: gr.State, module: str, outputs: list, to_updates):
    """При переході на вкладку автоматично відкриває останню незавершену вправу модуля.
    Нічого не змінює, якщо на вкладці вже відкрита вправа цього студента (щоб не затерти відповідь).
    to_updates(result) -> список значень для outputs (у тому ж порядку, що й після «Відкрити вправу»)."""
    from services import exercises
    from db import repo

    def resume(sid_, eid):
        skip = [gr.skip()] * len(outputs)
        try:
            if not sid_:
                return skip
            if eid and repo.get_exercise(sid_, eid):
                return skip
            r = exercises.resume_latest(sid_, module)
            return to_updates(r) if r else skip
        except Exception:
            log.exception("Auto-resume failed")  # не заважаємо перемиканню вкладки
            return skip

    tab.select(resume, [sid, ex_id], outputs)
