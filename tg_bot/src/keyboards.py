from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard():
    """Основная клавиатура бота"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        KeyboardButton(text="🔍 Поиск дела"),
        KeyboardButton(text="ℹ️ Помощь"),
        KeyboardButton(text="📊 Статистика")
    )
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_search_keyboard():
    """Клавиатура для поиска"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        KeyboardButton(text="📋 Примеры номеров дел"),
        KeyboardButton(text="⬅️ Назад")
    )
    
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_examples_keyboard():
    """Клавиатура с примерами номеров дел"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        KeyboardButton(text="А40-123456/2024"),
        KeyboardButton(text="А41-78901/2023"),
        KeyboardButton(text="А42-54321/2022"),
        KeyboardButton(text="⬅️ Назад к поиску")
    )
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    """Клавиатура для отмены действия"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(KeyboardButton(text="❌ Отмена"))
    
    return builder.as_markup(resize_keyboard=True)

# Inline клавиатуры
def get_inline_search_keyboard():
    """Inline клавиатура для быстрого поиска"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="🔍 Начать поиск", callback_data="start_search"),
        InlineKeyboardButton(text="📋 Примеры", callback_data="show_examples"),
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="show_help")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def get_inline_examples_keyboard():
    """Inline клавиатура с примерами"""
    builder = InlineKeyboardBuilder()
    
    examples = [
        ("А40-123456/2024", "А40-123456/2024"),
        ("А41-78901/2023", "А41-78901/2023"), 
        ("А42-54321/2022", "А42-54321/2022")
    ]
    
    for text, data in examples:
        builder.add(InlineKeyboardButton(text=text, callback_data=f"search:{data}"))
    
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()