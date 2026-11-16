import json
import os

import gradio as gr

from db import repo
from ui.common import guard, section_header

TOPICS = json.load(open(os.path.join("data", "topics.json"), encoding="utf-8"))
BANDS = [4.0 + 0.5 * i for i in range(11)]
INTRO = """
<div class="section-head">
  <h2>Ласкаво просимо до AI IELTS Tutor</h2>
  <p>Я ваш персональний AI-тьютор (не екзаменатор). Введіть <b>нікнейм</b>, він створює або відкриває ваш профіль.</p>
</div>
<div class="info-grid">
  <div class="info-card"><b>Speaking</b><span>Лише текстова практика: вимову та fluency я не оцінюю.</span></div>
  <div class="info-card"><b>Listening</b><span>Ви слухаєте матеріал на зовнішньому сайті і повертаєтеся з результатом.</span></div>
  <div class="info-card"><b>Writing</b><span>Band це неофіційна навчальна оцінка, не результат IELTS.</span></div>
</div>
"""


def build(sid: gr.State):
    gr.HTML(INTRO)
    with gr.Column(elem_classes="narrow"):
        nickname = gr.Textbox(label="Нікнейм", placeholder="наприклад: ihor2026")
        login = gr.Button("Увійти / створити профіль", variant="primary", elem_classes="cta")
        status = gr.Markdown(elem_classes="result")
    section_header("Налаштування профілю", sub=True, level=3)
    with gr.Group():
        display_name = gr.Textbox(label="Ім'я")
        with gr.Row():
            test_type = gr.Radio(["Academic", "General Training"], value="Academic", label="Тип IELTS")
            target = gr.Dropdown(BANDS, value=7.0, label="Цільовий band")
            level = gr.Dropdown(["unknown", "A2", "B1", "B2", "C1"], value="unknown", label="Поточний рівень (CEFR)")
        with gr.Row():
            exam = gr.Textbox(label="Дата іспиту (необов'язково, YYYY-MM-DD)")
            days = gr.Slider(1, 7, value=4, step=1, label="Днів на тиждень")
            minutes = gr.Slider(10, 120, value=30, step=5, label="Хвилин на заняття")
        topics = gr.CheckboxGroup(TOPICS, label="Улюблені теми")
        style = gr.Radio(["concise", "detailed"], value="detailed", label="Стиль feedback")
    save = gr.Button("Зберегти профіль", variant="primary", elem_classes="cta")
    fields = [display_name, test_type, target, level, exam, days, minutes, topics, style]

    @guard
    def do_login(nick):
        st = repo.get_or_create_student(nick)
        vals = [st["display_name"], st["test_type"], st["target_band"], st["current_level"],
                st["exam_date"] or "", st["weekly_study_days"], st["minutes_per_session"],
                st["topic_preferences"] or [], st["feedback_style"]]
        return [st["id"], f"Профіль **{st['nickname']}** відкрито. Перевірте налаштування й натисніть «Зберегти»."] + vals

    @guard
    def do_save(sid_, name, tt, tb, lv, ex, d, m, tp, fs):
        if not sid_:
            raise gr.Error("Спочатку увійдіть за нікнеймом.")
        st = repo.update_student(sid_, {"display_name": name or "Student", "test_type": tt,
                                        "target_band": float(tb), "current_level": lv,
                                        "exam_date": ex or None, "weekly_study_days": int(d),
                                        "minutes_per_session": int(m), "topic_preferences": tp,
                                        "feedback_style": fs})
        return "Збережено. Якщо змінили тип тесту чи ціль, створіть новий план на вкладці «Прогрес і план»."

    evt = login.click(do_login, nickname, [sid, status, *fields])
    save.click(do_save, [sid, *fields], status)
    return evt
