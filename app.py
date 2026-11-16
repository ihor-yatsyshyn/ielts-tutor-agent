"""ТИМЧАСОВИЙ app.py для першого коміту (Stage 1). Замінюється фінальним app.py в Stage 4."""
import gradio as gr

with gr.Blocks(title="AI IELTS Tutor") as demo:
    gr.Markdown("# 🎓 AI IELTS Tutor\nСкелет запущено. Розробка триває…")

if __name__ == "__main__":
    demo.launch()
