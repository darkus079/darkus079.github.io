from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Статус", callback_data="status")
    kb.button(text="История", callback_data="history")
    kb.button(text="Режим", callback_data="mode")
    kb.adjust(3)
    return kb.as_markup()


def parse_controls_kb(case: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="Статус", callback_data=f"status:{case}")
    kb.button(text="Отменить", callback_data=f"cancel:{case}")
    kb.adjust(2)
    return kb.as_markup()


