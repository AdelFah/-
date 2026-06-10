from groq import AsyncGroq
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """Ты — AI-ассистент для планирования задач в Telegram-боте. Твоя задача — помогать пользователю управлять расписанием, создавать задачи, оптимизировать планы дня и недели.

Текущая дата и время: {current_datetime}

Категории задач: учёба, работа, питание, спорт, отдых, личные, бытовые.
Приоритеты: low (низкий), medium (средний), high (высокий).

Когда пользователь хочет создать задачу — извлеки из сообщения:
- название задачи
- категорию (если не указана, угадай по контексту)
- дату и время (если указаны)
- дедлайн (если указан)
- приоритет (если указан)
- напоминание (если указано, в минутах до задачи)

Формат ответа — ТОЛЬКО JSON без лишнего текста:
{{
  "action": "create_task" | "show_today" | "show_week" | "show_pending" | "complete_task" | "delete_task" | "reschedule_task" | "analyze" | "chat",
  "task": {{
    "title": "...",
    "category": "...",
    "scheduled_at": "YYYY-MM-DD HH:MM" или null,
    "deadline_at": "YYYY-MM-DD HH:MM" или null,
    "priority": "low|medium|high",
    "description": null,
    "reminder_minutes": null
  }},
  "task_id": null,
  "new_time": null,
  "message": "Текст ответа пользователю на русском языке"
}}

Для обычного разговора используй action: "chat".
При анализе расписания используй action: "analyze".
Всегда отвечай на русском языке. Будь дружелюбным, используй эмодзи."""


def get_system_prompt() -> str:
    return SYSTEM_PROMPT.format(current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M, %A"))


async def process_message(user_message: str, conversation_history: list) -> dict:
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages += conversation_history
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.7,
        messages=messages,
    )

    raw = response.choices[0].message.content.strip()
    print(f"[GROQ] Ответ: {raw[:200]}")

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {"action": "chat", "message": raw}


async def analyze_schedule(tasks_today: list, tasks_week: list) -> str:
    tasks_text = "Задачи на сегодня:\n"
    for t in tasks_today:
        time_str = t.scheduled_at.strftime("%H:%M") if t.scheduled_at else "без времени"
        tasks_text += f"- {time_str}: {t.title} [{t.category}]\n"

    if not tasks_today:
        tasks_text += "- нет задач\n"

    tasks_text += "\nЗадачи на неделю:\n"
    for t in tasks_week:
        time_str = t.scheduled_at.strftime("%d.%m %H:%M") if t.scheduled_at else "без времени"
        tasks_text += f"- {time_str}: {t.title} [{t.category}]\n"

    prompt = f"{tasks_text}\n\nПроанализируй расписание на русском языке. Найди перегруженные дни, свободные окна, дай советы."

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()
