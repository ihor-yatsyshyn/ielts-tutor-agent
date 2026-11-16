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
