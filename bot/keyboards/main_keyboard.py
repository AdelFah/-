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
        [
            InlineKeyboardButton("🔄 Перенести", callback_data=f"move_{task_id}"),
            InlineKeyboardButton("✏️ Переименовать", callback_data=f"rename_{task_id}"),
        ],
        [
            InlineKeyboardButton("🎯 Приоритет", callback_data=f"priority_{task_id}"),
            InlineKeyboardButton("📂 Категория", callback_data=f"category_{task_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def priority_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 Высокий", callback_data=f"setpri_high_{task_id}"),
            InlineKeyboardButton("🟡 Средний", callback_data=f"setpri_medium_{task_id}"),
            InlineKeyboardButton("🟢 Низкий", callback_data=f"setpri_low_{task_id}"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"task_{task_id}")],
    ])


def category_keyboard(task_id: int) -> InlineKeyboardMarkup:
    cats = [
        ("📚 Учёба", "учёба"), ("💼 Работа", "работа"), ("🍽 Питание", "питание"),
        ("🏋️ Спорт", "спорт"), ("😴 Отдых", "отдых"), ("👤 Личные", "личные"),
        ("🏠 Бытовые", "бытовые"),
    ]
    rows = []
    row = []
    for label, val in cats:
        row.append(InlineKeyboardButton(label, callback_data=f"setcat_{val}_{task_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data=f"task_{task_id}")])
    return InlineKeyboardMarkup(rows)


def tasks_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
    keyboard = []
    for task in tasks[:10]:
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
