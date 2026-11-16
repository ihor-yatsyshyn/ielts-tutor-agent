# 🎓 AI IELTS Tutor

Адаптивний AI-тьютор для підготовки до IELTS (Academic / General Training).
Один центральний агент (Groq LLM + tool calling), Gradio UI, SQLite. Запускається **локально**.

**Межі продукту:** лише текстова взаємодія. Speaking: текстова практика (без вимови/fluency/band).
Listening: зовнішні ресурси + звіт студента. Writing-band: неофіційна навчальна оцінка.
Правильність Reading рахує код за ключем, а не LLM.

## Швидкий старт
```bash
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1 ; Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env                 # впишіть свій GROQ_API_KEY (https://console.groq.com/keys)
python app.py                        # http://127.0.0.1:7860
pytest -q                            # тести (мережа й ключ не потрібні)
```

## Налаштування (`.env`)
| Змінна | Опис |
|---|---|
| `GROQ_API_KEY` | ключ Groq (**не комітити**, файл `.env` в `.gitignore`) |
| `GROQ_MODEL` | модель з tool use, за замовчуванням `llama-3.3-70b-versatile` (актуальні: console.groq.com/docs/models) |
| `DATABASE_URL` | за замовчуванням `sqlite:///./data/ielts_tutor.db` |
| `APP_HOST` / `APP_PORT` | за замовчуванням `127.0.0.1` / `7860` |

## Структура
```
app.py              точка входу Gradio
config.py errors.py налаштування, типи помилок
db/                 SQLAlchemy-моделі, сесія, репозиторій (єдине місце з SQL)
agent/              LLM-адаптер (Groq), промпт, tools, цикл агента
services/           прогрес, планувальник, оркестрація вправ
modules/            writing / reading / speaking / listening
ui/                 вкладки Gradio
data/               каталог Listening, теми
tests/              pytest (FakeLLM, без мережі)
docs/GUIDE.md       інструкція для команди (гілки, коміти, ролі)
```

## Відомі обмеження
- Вхід за нікнеймом без пароля (локальний MVP).
- Немає export/delete даних, автозбереження чернеток, графіків, див. backlog у `docs/GUIDE.md`.
- Listening-каталог: «хаби» джерел; конкретні перевірені вправи додаються в `data/listening_resources.json`.
