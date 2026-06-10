from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        ["📅 Сегодня", "📆 Неделя"],
        ["➕ Добавить задачу", "📋 Все задачи"],
        ["🤖 Спросить ИИ", "📊 Аналитика"],
        ["📓 Заметки"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Выполнено", callback_data=f"done_{task_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{task_id}"),
        ],
        [InlineKeyboardButton("🔄 Перенести", callback_data=f"move_{task_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def tasks_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
    keyboard = []
    for task in tasks[:10]:  # Показываем максимум 10
        status = "✅" if task.status == "done" else "⏳"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} #{task.id} {task.title[:30]}",
                callback_data=f"task_{task.id}"
            )
        ])
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(action: str, task_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}_{task_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
