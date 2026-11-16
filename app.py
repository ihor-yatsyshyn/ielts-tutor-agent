"""Точка входу Gradio (локальний запуск: python app.py)."""
import logging
import os

import gradio as gr

import config
from db.session import init_db
from ui.theme import CSS, HEADER_HTML, THEME
from ui import chat_tab, listening_tab, profile_tab, progress_tab, reading_tab, speaking_tab, writing_tab

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
init_db()


def build_app() -> gr.Blocks:
    with gr.Blocks(title="AI IELTS Tutor", theme=THEME, css=CSS) as demo:
        sid = gr.State("")  # student_id поточної сесії браузера
        gr.HTML(HEADER_HTML)
        with gr.Tabs():
            with gr.Tab("Профіль"):
                login_evt = profile_tab.build(sid)
            with gr.Tab("Tutor Chat"):
                chatbot = chat_tab.build(sid)
            with gr.Tab("Writing"):
                writing_tab.build(sid)
            with gr.Tab("Reading"):
                reading_tab.build(sid)
            with gr.Tab("Listening"):
                listening_tab.build(sid)
            with gr.Tab("Speaking"):
                speaking_tab.build(sid)
            with gr.Tab("Прогрес і план"):
                progress_tab.build(sid)
        login_evt.then(chat_tab.load_history, sid, chatbot)  # підвантажити історію чату після входу
    return demo


demo = build_app()

if __name__ == "__main__":
    demo.queue().launch(server_name=os.getenv("APP_HOST", "127.0.0.1"),
                        server_port=int(os.getenv("APP_PORT", "7860")))
