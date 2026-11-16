import json

import gradio as gr

from db import repo
from services import exercises
from ui.common import guard, need_sid, open_by_id_widgets, resume_on_select, section_header

TOPICS = json.load(open("data/topics.json", encoding="utf-8"))
MAXQ = 8


def _box_updates(qs):
    upd = []
    for i in range(MAXQ):
        if i < len(qs):
            hint = {"tfng": "TRUE / FALSE / NOT GIVEN", "mcq": "літера A-D", "short": "до 3 слів"}[qs[i]["type"]]
            upd.append(gr.update(visible=True, value="", label=f"Q{qs[i]['id']}: {hint}"))
        else:
            upd.append(gr.update(visible=False, value=""))
    return upd


def build(sid: gr.State, tab: gr.Tab | None = None):
    section_header("Reading", "Правильність рахує <b>код за ключем</b> (verified). Ключ не показується до відправки.")
    with gr.Row():
        topic = gr.Dropdown(TOPICS, value=None, allow_custom_value=True, label="Тема (необов'язково)")
        new = gr.Button("Новий текст", variant="primary")
    pick, open_btn = open_by_id_widgets(sid, "reading")
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
        return [r["exercise_id"], r["display_markdown"], gr.update(visible=True), ""] + _box_updates(qs)

    @guard
    def do_open(sid_, raw):
        need_sid(sid_)
        r = exercises.open_exercise(sid_, raw, "reading")
        return ([r["exercise_id"], r["display_markdown"], gr.update(visible=True), ""]
                + _box_updates(r["content"]["questions"]))

    @guard
    def do_submit(sid_, eid, *vals):
        need_sid(sid_)
        if not eid:
            raise gr.Error("Спочатку згенеруйте текст.")
        answers = {str(i + 1): v for i, v in enumerate(vals) if (v or "").strip()}
        return exercises.submit(sid_, eid, answers=answers)["markdown"]

    new.click(do_new, [sid, topic], [ex_id, passage, submit, result, *boxes])
    open_btn.click(do_open, [sid, pick], [ex_id, passage, submit, result, *boxes])
    submit.click(do_submit, [sid, ex_id, *boxes], result)
    if tab is not None:  # автовідкриття незавершеної вправи при переході на вкладку
        resume_on_select(tab, sid, ex_id, "reading", [ex_id, passage, submit, result, *boxes],
                         lambda r: [r["exercise_id"], r["display_markdown"], gr.update(visible=True), ""]
                         + _box_updates(r["content"]["questions"]))
