import json

import gradio as gr

from services import exercises
from ui.common import guard, need_sid, open_by_id_widgets, resume_on_select, section_header

TOPICS = json.load(open("data/topics.json", encoding="utf-8"))


def build(sid: gr.State, tab: gr.Tab | None = None):
    section_header("Speaking (текстова практика)")
    gr.HTML('<div class="note">Text-based practice: <b>pronunciation is not assessed</b>. Загального Speaking band немає.</div>')
    with gr.Row():
        part = gr.Radio([("Part 1", "part1"), ("Part 2", "part2"), ("Part 3", "part3")], value="part1", label="Частина")
        topic = gr.Dropdown(TOPICS, value=None, allow_custom_value=True, label="Тема")
        new = gr.Button("Нове запитання", variant="primary")
    pick, open_btn = open_by_id_widgets(sid, "speaking")
    ex_id = gr.State("")
    prompt = gr.Markdown(elem_classes=["result", "task-box"])
    answer = gr.Textbox(lines=8, label="Ваша відповідь (текстом)")
    submit = gr.Button("Отримати feedback", variant="primary", elem_classes="cta")
    feedback = gr.Markdown(elem_classes="result")

    @guard
    def do_new(sid_, p, tp):
        need_sid(sid_)
        r = exercises.generate(sid_, "speaking", p, tp)
        return r["exercise_id"], r["display_markdown"], "", ""

    @guard
    def do_open(sid_, raw):
        need_sid(sid_)
        r = exercises.open_exercise(sid_, raw, "speaking")
        return r["exercise_id"], r["display_markdown"], "", ""

    @guard
    def do_submit(sid_, eid, text):
        need_sid(sid_)
        if not eid:
            raise gr.Error("Спочатку отримайте запитання.")
        return exercises.submit(sid_, eid, answer_text=text)["markdown"]

    new.click(do_new, [sid, part, topic], [ex_id, prompt, answer, feedback])
    open_btn.click(do_open, [sid, pick], [ex_id, prompt, answer, feedback])
    submit.click(do_submit, [sid, ex_id, answer], feedback)
    if tab is not None:  # автовідкриття незавершеної вправи при переході на вкладку
        resume_on_select(tab, sid, ex_id, "speaking", [ex_id, prompt, answer, feedback],
                         lambda r: [r["exercise_id"], r["display_markdown"], "", ""])
