import json

import gradio as gr

from db import repo
from modules import listening
from ui.common import guard, need_sid, section_header

TOPICS = json.load(open("data/topics.json", encoding="utf-8"))


def _render(res):
    md = "\n".join(f"- **{r['title']}** ({r['provider']}, {r['level']}): {r['url']}  \n  _{r.get('usage_notes', '')}_"
                   for r in res)
    upd = gr.update(choices=[(f"{r['title']} ({r['provider']})", r["resource_id"]) for r in res],
                    value=res[0]["resource_id"] if res else None)
    return md, upd


def _pending_choices(sid_):
    if not sid_:
        return gr.update(choices=[], value=None)
    rows = repo.list_listening_assignments(sid_, "assigned")
    ch = [(r["resource_snapshot_json"].get("title", r["resource_id"]), r["id"]) for r in rows]
    return gr.update(choices=ch, value=ch[-1][1] if ch else None)


def build(sid: gr.State):
    section_header("Listening (зовнішні ресурси)",
                   "Аудіо тут <b>не відтворюється</b>: відкрийте ресурс, виконайте вправу на сайті й внесіть результат. "
                   "Ваш рахунок зберігається як <b>self-reported</b>.")
    with gr.Row():
        level = gr.Dropdown(["", "A2", "B1", "B2", "C1"], value="", label="Рівень")
        topic = gr.Dropdown(TOPICS, value=None, allow_custom_value=True, label="Тема (необов'язково)")
        find = gr.Button("Знайти ресурси", variant="primary")
    init_md, init_upd = _render(listening.search(None, None, 10))
    found = gr.Markdown(init_md, elem_classes="result")
    res_choice = gr.Dropdown(init_upd["choices"], value=init_upd["value"], label="Оберіть ресурс (джерело)")
    goal = gr.Textbox(label="Мета (необов'язково)")
    assign = gr.Button("Призначити", variant="primary", elem_classes="cta")
    instr = gr.Markdown(elem_classes="result")
    section_header("Повернулися з вправи?", sub=True, level=3)
    pending = gr.Dropdown([], label="Призначена вправа")
    with gr.Row():
        correct = gr.Number(label="Правильних", precision=0, value=None)
        total = gr.Number(label="Всього питань", precision=0, value=None)
    difficult = gr.Textbox(label="Складні питання (через кому, напр. 3, 7)")
    words = gr.Textbox(label="Незнайомі слова (через кому)")
    notes = gr.Textbox(label="Нотатки", lines=2)
    submit = gr.Button("Зберегти результат", variant="primary", elem_classes="cta")
    out = gr.Markdown(elem_classes="result")

    @guard
    def do_find(lv, tp):
        return _render(listening.search(lv or None, tp or None, 10))

    @guard
    def do_assign(sid_, rid, g):
        need_sid(sid_)
        if not rid:
            raise gr.Error("Оберіть ресурс.")
        return listening.assign(sid_, rid, g)["display_markdown"], _pending_choices(sid_)

    @guard
    def do_submit(sid_, aid, c, t, d, w, n):
        need_sid(sid_)
        if not aid:
            raise gr.Error("Оберіть призначену вправу.")
        split = lambda s: [x.strip() for x in (s or "").split(",") if x.strip()]
        r = listening.submit(sid_, aid, None if c is None else int(c), None if t is None else int(t),
                             split(d), split(w), n)
        return r["display_markdown"], _pending_choices(sid_)

    find.click(do_find, [level, topic], [found, res_choice])
    level.change(do_find, [level, topic], [found, res_choice])
    topic.change(do_find, [level, topic], [found, res_choice])
    assign.click(do_assign, [sid, res_choice, goal], [instr, pending])
    submit.click(do_submit, [sid, pending, correct, total, difficult, words, notes], [out, pending])
    return pending
