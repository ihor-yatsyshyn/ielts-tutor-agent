import gradio as gr
import pandas as pd

from services import planner
from services.progress import get_progress
from db import repo
from ui.common import guard, need_sid, section_header


def build(sid: gr.State):
    section_header("Прогрес і план", "Статистика по модулях, повторювані помилки та персональний план на 14 днів.")
    with gr.Row(elem_classes="actions"):
        period = gr.Radio([("7 днів", 7), ("30 днів", 30), ("90 днів", 90), ("весь час", 3650)], value=90, label="Період")
    with gr.Row(elem_classes="actions"):
        refresh = gr.Button("Оновити", variant="primary")
        mkplan = gr.Button("Створити/оновити план (14 днів)", variant="secondary")
    rec = gr.Markdown(elem_classes="result")
    table = gr.Dataframe(label="По модулях (з джерелом оцінки)", interactive=False, wrap=True)
    mist = gr.Dataframe(label="Повторювані помилки", interactive=False, wrap=True)
    plan_md = gr.Markdown(elem_classes="result")

    def _plan_text(sid_):
        p = repo.get_active_plan(sid_)
        if not p:
            return "_Плану ще немає. Натисніть «Створити/оновити план»._"
        head = f"### План v{p['version']} ({p['status']})\n_{p['rationale']}_\n"
        rows = [f"- тиждень {i['week']}, заняття {i['slot']}: **{i['module']}** · {i['minutes']} хв" for i in p["items_json"][:14]]
        return head + "\n".join(rows)

    @guard
    def do_refresh(sid_, days):
        need_sid(sid_)
        prog = get_progress(sid_, int(days))
        nxt = planner.get_next_activity(sid_)
        rows = [{"модуль": m, "статус": v["status"], "спроб": v["attempts"], "показник": v["metric"],
                 "значення": v["value"], "джерело": "/".join(v["provenance"]), "тренд": v["trend"],
                 "остання практика": v["last_practiced_at"][:10]} for m, v in prog["modules"].items()]
        ms = pd.DataFrame(prog["open_mistakes"] or [{"module": "-", "subskill": "-", "original": "-",
                                                       "correction": "-", "times": 0, "status": "-"}])
        rec_md = f"### Наступний крок\n**{nxt['reason']}**" + (f"\n\nМодуль: `{nxt.get('module')}`" if nxt.get("module") else "")
        return rec_md, pd.DataFrame(rows), ms, _plan_text(sid_)

    @guard
    def do_plan(sid_):
        need_sid(sid_)
        planner.create_plan(sid_, 14)
        return _plan_text(sid_)

    refresh.click(do_refresh, [sid, period], [rec, table, mist, plan_md])
    mkplan.click(do_plan, sid, plan_md)
