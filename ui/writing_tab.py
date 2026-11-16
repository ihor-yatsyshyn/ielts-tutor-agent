import json
import uuid

import gradio as gr

from services import exercises
from ui.common import guard, need_sid, open_by_id_widgets, resume_on_select, section_header

TOPICS = json.load(open("data/topics.json", encoding="utf-8"))


def build(sid: gr.State, tab: gr.Tab | None = None):
    section_header("Writing", "Фідбек за критеріями IELTS. <b>Band: неофіційна навчальна оцінка.</b>")
    with gr.Row():
        task = gr.Radio([("Task 2 (есе)", "task2"), ("Task 1 (залежить від типу тесту)", "task1")],
                        value="task2", label="Тип")
        topic = gr.Dropdown(TOPICS, value=None, allow_custom_value=True, label="Тема (необов'язково)")
    new = gr.Button("Нова вправа", variant="primary", elem_classes="cta")
    pick, open_btn = open_by_id_widgets(sid, "writing")
    ex_id, sub_id = gr.State(""), gr.State("")
    prompt = gr.Markdown(elem_classes=["result", "task-box"])
    essay = gr.Textbox(lines=14, label="Ваш текст", placeholder="Напишіть відповідь тут…")
    counter = gr.Markdown("Слів: 0")
    submit = gr.Button("Перевірити", variant="primary", elem_classes="cta")
    feedback = gr.Markdown(elem_classes="result")

    @guard
    def do_new(sid_, t, tp):
        need_sid(sid_)
        r = exercises.generate(sid_, "writing", t, tp)
        return r["exercise_id"], str(uuid.uuid4()), r["display_markdown"], "", "Слів: 0", ""

    @guard
    def do_open(sid_, raw):
        need_sid(sid_)
        r = exercises.open_exercise(sid_, raw, "writing")
        return r["exercise_id"], str(uuid.uuid4()), r["display_markdown"], "", "Слів: 0", ""

    @guard
    def do_submit(sid_, eid, subid, text):
        need_sid(sid_)
        if not eid:
            raise gr.Error("Спочатку натисніть «Нова вправа».")
        return exercises.submit(sid_, eid, answer_text=text, submission_id=eid)["markdown"]

    new.click(do_new, [sid, task, topic], [ex_id, sub_id, prompt, essay, counter, feedback])
    open_btn.click(do_open, [sid, pick], [ex_id, sub_id, prompt, essay, counter, feedback])
    essay.change(lambda t: f"Слів: {len((t or '').split())}", essay, counter)
    submit.click(do_submit, [sid, ex_id, sub_id, essay], feedback)
    if tab is not None:  # автовідкриття незавершеної вправи при переході на вкладку
        resume_on_select(tab, sid, ex_id, "writing", [ex_id, sub_id, prompt, essay, counter, feedback],
                         lambda r: [r["exercise_id"], str(uuid.uuid4()), r["display_markdown"], "", "Слів: 0", ""])
