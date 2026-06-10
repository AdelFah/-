from openai import AsyncOpenAI
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

Формат ответа — JSON когда нужно выполнить действие:
{
  "action": "create_task" | "show_today" | "show_week" | "show_pending" | "complete_task" | "delete_task" | "reschedule_task" | "analyze" | "chat",
  "task": {
    "title": "...",
    "category": "...",
    "scheduled_at": "YYYY-MM-DD HH:MM" или null,
    "deadline_at": "YYYY-MM-DD HH:MM" или null,
    "priority": "low|medium|high",
    "description": "..." или null,
    "reminder_minutes": число или null
  },
  "task_id": число (для complete/delete/reschedule),
  "new_time": "YYYY-MM-DD HH:MM" (для reschedule),
  "message": "Текст ответа пользователю"
}

Для обычного разговора или советов используй action: "chat" и пиши ответ в message.

При анализе продуктивности (action: "analyze") дай конкретные советы.
Будь дружелюбным, лаконичным, используй эмодзи."""


def get_system_prompt() -> str:
    return SYSTEM_PROMPT.format(current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M, %A"))


async def process_message(user_message: str, conversation_history: list) -> dict:
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages += conversation_history
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        messages=messages,
    )

    raw = response.choices[0].message.content.strip()

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            json_str = raw[start:end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    return {"action": "chat", "message": raw}


async def analyze_schedule(tasks_today: list, tasks_week: list) -> str:
    tasks_text = "Задачи на сегодня:\n"
    for t in tasks_today:
        time_str = t.scheduled_at.strftime("%H:%M") if t.scheduled_at else "без времени"
        tasks_text += f"- {time_str}: {t.title} [{t.category}]\n"

    if not tasks_today:
        tasks_text += "- нет задач на сегодня\n"

    tasks_text += "\nЗадачи на неделю:\n"
    for t in tasks_week:
        time_str = t.scheduled_at.strftime("%d.%m %H:%M") if t.scheduled_at else "без времени"
        tasks_text += f"- {time_str}: {t.title} [{t.category}]\n"

    prompt = f"{tasks_text}\n\nПроанализируй расписание. Найди:\n1. Перегруженные дни\n2. Свободные временные окна\n3. Дай советы по оптимизации\n4. Предупреди о рисках."

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=800,
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()
