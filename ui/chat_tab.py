import gradio as gr

from agent.tutor import handle_user_turn
from db import repo
from ui.common import guard, need_sid, section_header


def load_history(sid_):
    if not sid_:
        return []
    return [{"role": m["role"], "content": m["content"]} for m in repo.recent_messages(sid_, 50)]


def build(sid: gr.State):
    section_header("AI Tutor Chat", "Питайте про правила, просіть вправу («дай Writing Task 2»), "
                   "надсилайте відповіді або запитуйте «що мені робити сьогодні?».")
    chat = gr.Chatbot(type="messages", height="55vh", min_height=320, show_label=False,
                      elem_classes="chat-box", placeholder="Почніть розмову з тьютором")
    box = gr.Textbox(placeholder="Напишіть повідомлення…", show_label=False, lines=2)
    with gr.Row(elem_classes="actions"):
        send = gr.Button("Надіслати", variant="primary")
        quick = gr.Button("Що робити сьогодні?", variant="secondary")

    @guard
    def respond(msg, history, sid_):
        need_sid(sid_)
        history = list(history or [])
        history.append({"role": "user", "content": msg})
        reply = handle_user_turn(sid_, msg)
        history.append({"role": "assistant", "content": reply})
        return "", history

    send.click(respond, [box, chat, sid], [box, chat])
    box.submit(respond, [box, chat, sid], [box, chat])
    quick.click(lambda: "Що мені робити сьогодні?", None, box).then(respond, [box, chat, sid], [box, chat])
    return chat
