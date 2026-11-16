import json

import gradio as gr

from db import repo
from services import exercises
from ui.common import guard, need_sid, section_header

TOPICS = json.load(open("data/topics.json", encoding="utf-8"))
MAXQ = 8


def build(sid: gr.State):
    section_header("Reading", "Правильність рахує <b>код за ключем</b> (verified). Ключ не показується до відправки.")
    with gr.Row():
        topic = gr.Dropdown(TOPICS, value=None, allow_custom_value=True, label="Тема (необов'язково)")
        new = gr.Button("Новий текст", variant="primary")
    ex_id = gr.State("")
    passage = gr.Markdown(elem_classes=["result", "task-box"])
    boxes = [gr.Textbox(visible=False, label=f"Q{i + 1}") for i in range(MAXQ)]
    submit = gr.Button("Перевірити", variant="primary", visible=False, elem_classes="cta")
    result = gr.Markdown(elem_classes="result")

    @guard
    def do_new(sid_, tp):
        need_sid(sid_)
        r = exercises.generate(sid_, "reading", None, tp)
        ex = repo.get_exercise(sid_, r["exercise_id"])
        qs = ex["content_json"]["questions"]
        upd = []
        for i in range(MAXQ):
            if i < len(qs):
                hint = {"tfng": "TRUE / FALSE / NOT GIVEN", "mcq": "літера A-D", "short": "до 3 слів"}[qs[i]["type"]]
                upd.append(gr.update(visible=True, value="", label=f"Q{qs[i]['id']}: {hint}"))
            else:
                upd.append(gr.update(visible=False, value=""))
        return [r["exercise_id"], r["display_markdown"], gr.update(visible=True), ""] + upd

    @guard
    def do_submit(sid_, eid, *vals):
        need_sid(sid_)
        if not eid:
            raise gr.Error("Спочатку згенеруйте текст.")
        answers = {str(i + 1): v for i, v in enumerate(vals) if (v or "").strip()}
        return exercises.submit(sid_, eid, answers=answers)["markdown"]

    new.click(do_new, [sid, topic], [ex_id, passage, submit, result, *boxes])
    submit.click(do_submit, [sid, ex_id, *boxes], result)
