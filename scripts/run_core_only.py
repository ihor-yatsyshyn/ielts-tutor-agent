"""Локальний запуск лише Профіль + Chat (для розробника агента, поки модулі ще не змержені).
python scripts/run_core_only.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gradio as gr  # noqa: E402

from db.session import init_db  # noqa: E402
from ui import chat_tab, profile_tab  # noqa: E402

init_db()
with gr.Blocks(title="core-only") as demo:
    sid = gr.State("")
    with gr.Tab("Профіль"):
        evt = profile_tab.build(sid)
    with gr.Tab("Chat"):
        chat = chat_tab.build(sid)
    evt.then(chat_tab.load_history, sid, chat)

if __name__ == "__main__":
    demo.queue().launch()
