"""Тема та CSS: синій акцент, центрована адаптивна верстка."""
import gradio as gr

THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.blue,
    secondary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.slate,
    radius_size=gr.themes.sizes.radius_lg,
    font=["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
).set(
    button_primary_background_fill="linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
    button_primary_background_fill_hover="linear-gradient(135deg, #2563eb 0%, #1e40af 100%)",
    button_primary_text_color="white",
    button_primary_shadow="0 6px 16px rgba(37, 99, 235, 0.28)",
    block_title_text_weight="600",
    block_label_text_weight="600",
)

CSS = """
:root {
  --accent: #2563eb;
  --accent-dark: #1d4ed8;
  --accent-soft: #eff6ff;
  --accent-line: #bfdbfe;
  --card-bg: #ffffff;
  --card-border: #e2e8f0;
  --card-shadow: 0 10px 30px rgba(30, 64, 175, 0.07);
  --muted: #64748b;
}
.dark {
  --accent: #60a5fa;
  --accent-dark: #3b82f6;
  --accent-soft: rgba(59, 130, 246, 0.14);
  --accent-line: rgba(96, 165, 250, 0.35);
  --card-bg: #111827;
  --card-border: #1f2937;
  --card-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  --muted: #94a3b8;
}

footer { display: none !important; }

body, gradio-app, .gradio-container {
  background:
    radial-gradient(900px 420px at 50% -120px, rgba(59, 130, 246, 0.16), transparent 70%),
    var(--body-background-fill) !important;
}
.dark body, .dark gradio-app, .dark .gradio-container {
  background:
    radial-gradient(900px 420px at 50% -120px, rgba(59, 130, 246, 0.20), transparent 70%),
    var(--body-background-fill) !important;
}

.gradio-container {
  max-width: 980px !important;
  margin: 0 auto !important;
  padding: 0 18px 48px !important;
}

/* ---------- Заголовок ---------- */
.app-header { text-align: center; padding: 38px 8px 22px; }
.app-header h1 {
  margin: 0 0 8px;
  font-size: clamp(1.9rem, 5.5vw, 2.8rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.app-header .logo { margin-right: 6px; }
.app-header .grad {
  background: linear-gradient(135deg, #60a5fa 0%, #2563eb 55%, #1e40af 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
.app-header p {
  margin: 0 auto;
  max-width: 560px;
  color: var(--muted);
  font-size: clamp(0.95rem, 2.6vw, 1.05rem);
}

/* ---------- Вкладки ---------- */
.tab-wrapper, .tab-container { justify-content: center; }
.tab-container { border-bottom-color: transparent !important; gap: 4px; }
.tab-container::after { display: none !important; }
.tab-container button[role="tab"] {
  border-radius: 999px !important;
  padding: 8px 18px !important;
  font-weight: 600;
  color: var(--muted);
  border: 1px solid transparent !important;
  transition: all .15s ease;
}
.tab-container button[role="tab"]:hover { color: var(--accent); background: var(--accent-soft); }
.tab-container button[role="tab"].selected {
  color: #fff !important;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
}
.tab-container button[role="tab"].selected::after { display: none !important; }
.tabitem {
  background: var(--card-bg) !important;
  border: 1px solid var(--card-border) !important;
  border-radius: 22px !important;
  box-shadow: var(--card-shadow);
  margin-top: 14px;
  padding: clamp(16px, 4vw, 32px) !important;
}

/* ---------- Заголовки розділів ---------- */
.section-head { text-align: center; margin: 4px auto 18px; max-width: 680px; }
.section-head h2 {
  margin: 0 0 6px;
  font-size: clamp(1.35rem, 4vw, 1.75rem);
  font-weight: 800;
  letter-spacing: -0.01em;
}
.section-head h3 { margin: 0 0 4px; font-size: 1.15rem; font-weight: 700; }
.section-head p { margin: 0; color: var(--muted); line-height: 1.55; }
.section-head.sub { margin-top: 22px; }

.note {
  max-width: 680px;
  margin: 0 auto 8px;
  padding: 10px 16px;
  border-radius: 14px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  color: var(--body-text-color);
  text-align: center;
  font-size: 0.95rem;
}

.info-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin: 6px 0 4px;
}
.info-card {
  flex: 1 1 200px;
  max-width: 300px;
  padding: 14px 16px;
  border-radius: 16px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  text-align: center;
}
.info-card b { display: block; color: var(--accent); margin-bottom: 4px; font-size: 1rem; }
.info-card span { color: var(--muted); font-size: 0.9rem; line-height: 1.45; }

/* ---------- Центрування і розміри блоків ---------- */
.narrow { max-width: 620px; margin-left: auto !important; margin-right: auto !important; width: 100%; }
.actions { justify-content: center !important; gap: 12px; }
.actions > * { flex: 0 1 auto !important; min-width: 180px !important; }
button.cta {
  align-self: center;
  width: min(100%, 340px) !important;
  min-width: 0 !important;
  margin: 6px auto 0;
}
button.primary, button.secondary { font-weight: 700; }
button.secondary { border: 1px solid var(--accent-line) !important; color: var(--accent) !important; background: var(--accent-soft) !important; }
button.secondary:hover { filter: brightness(0.97); }

div.row { flex-wrap: wrap !important; gap: 14px; }
div.row > * { min-width: 160px; }

/* ---------- Результати ---------- */
.result { text-align: left; }
.result table { margin-left: auto; margin-right: auto; }
.result .prose, .result.prose { font-size: 0.98rem; line-height: 1.65; }
.result blockquote { border-left: 3px solid var(--accent) !important; background: var(--accent-soft); border-radius: 0 10px 10px 0; padding: 6px 12px; }
.result h3 { color: var(--accent); }

.task-box {
  border: 1px solid var(--accent-line);
  border-radius: 16px;
  padding: 4px 18px;
  background: var(--accent-soft);
}
.task-box:has(.prose:empty) { display: none; }

/* ---------- Чат ---------- */
.chat-box { border-radius: 18px !important; }

/* ---------- Мобільні ---------- */
@media (max-width: 640px) {
  main.fillable { padding-left: 6px !important; padding-right: 6px !important; }
  .app-header { padding-top: 24px; }
  .tab-container button[role="tab"] { padding: 7px 12px !important; font-size: 0.9rem; }
  div.row { flex-direction: column !important; }
  div.row > * { width: 100% !important; min-width: 0 !important; flex: 1 1 auto !important; }
  .actions > * { min-width: 0 !important; width: 100% !important; }
  .tabitem { border-radius: 18px !important; }
}
"""

HEADER_HTML = """
<div class="app-header">
  <h1><span class="logo">🎓</span><span class="grad">AI IELTS Tutor</span></h1>
  <p>Персональний AI-тьютор для підготовки до IELTS: Writing, Reading, Listening і Speaking в одному місці.</p>
</div>
"""
