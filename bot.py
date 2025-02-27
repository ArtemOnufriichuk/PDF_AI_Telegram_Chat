#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram PDF Chat Bot
--------------------
Бот для анализа PDF документов и ответов на вопросы по их содержанию.
Использует ChatPDF API для обработки документов и генерации ответов.
"""

import os
import re
import requests
import asyncio
import nest_asyncio
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Применяем nest_asyncio для поддержки вложенных циклов событий
nest_asyncio.apply()

# ------------------------------------------------------------------------------
# КОНФИГУРАЦИЯ И КОНСТАНТЫ
# ------------------------------------------------------------------------------

# API токены и ключи
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set. Please check your .env file.")

CHATPDF_API_KEY = os.environ.get("CHATPDF_API_KEY")
if not CHATPDF_API_KEY:
    raise ValueError("CHATPDF_API_KEY environment variable is not set. Please check your .env file.")

# API endpoints для ChatPDF
CHATPDF_API = {
    "ADD_FILE": "https://api.chatpdf.com/v1/sources/add-file",
    "CHAT": "https://api.chatpdf.com/v1/chats/message",
    "DELETE": "https://api.chatpdf.com/v1/sources/delete"
}

# Структура для хранения пользовательских данных
# user_id: {
#     "sourceId": str,          # ID документа в ChatPDF
#     "messages": List[dict],   # История сообщений
#     "current_pdf": str        # Имя текущего PDF файла
# }
user_data: Dict[int, Dict] = {}

# ------------------------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ------------------------------------------------------------------------------

def format_text(text: str) -> str:
    """
    Форматирует текст ответа:
    - Преобразует **текст** в HTML-теги <b>текст</b>
    - Добавляет иконку перед ответом
    """
    formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return f"🤖 Ответ:\n{formatted}"

def create_inline_keyboard() -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру с основными действиями"""
    keyboard = [
        [InlineKeyboardButton("📥 Загрузить новый PDF", callback_data="new_chat")],
        [InlineKeyboardButton("🔄 Очистить историю", callback_data="clear_history")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ------------------------------------------------------------------------------
# ФУНКЦИИ ДЛЯ РАБОТЫ С CHATPDF API
# ------------------------------------------------------------------------------

def upload_pdf_to_chatpdf(file_path: str) -> str:
    """
    Загружает PDF файл в ChatPDF API.
    Returns:
        str: ID загруженного документа
    Raises:
        requests.exceptions.RequestException: при ошибке API
    """
    headers = {"x-api-key": CHATPDF_API_KEY}
    with open(file_path, "rb") as pdf_file:
        files = {
            "file": (
                os.path.basename(file_path),
                pdf_file,
                "application/pdf"
            )
        }
        response = requests.post(CHATPDF_API["ADD_FILE"], headers=headers, files=files)
    response.raise_for_status()
    return response.json()["sourceId"]

def ask_chatpdf(source_id: str, messages: List[Dict]) -> Dict:
    """
    Отправляет вопрос к ChatPDF API и получает ответ.
    Args:
        source_id: ID документа в ChatPDF
        messages: История сообщений
    Returns:
        Dict: Ответ от API
    """
    headers = {
        "x-api-key": CHATPDF_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "sourceId": source_id,
        "referenceSources": True,
        "messages": messages
    }
    response = requests.post(CHATPDF_API["CHAT"], headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def delete_pdf_from_chatpdf(source_id: str) -> None:
    """Удаляет PDF документ из ChatPDF API"""
    headers = {
        "x-api-key": CHATPDF_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"sources": [source_id]}
    response = requests.post(CHATPDF_API["DELETE"], headers=headers, json=payload)
    response.raise_for_status()

# ------------------------------------------------------------------------------
# ОБРАБОТЧИКИ КОМАНД
# ------------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - отправляет приветственное сообщение"""
    welcome_message = (
        "👋 Добро пожаловать в PDF Чат Ассистент!\n\n"
        "Я помогу вам анализировать PDF документы и отвечать на вопросы по их содержанию. Как использовать:\n\n"
        "1️⃣ Отправьте мне PDF файл\n"
        "2️⃣ После загрузки задавайте любые вопросы по содержанию\n"
        "3️⃣ Используйте /reset чтобы очистить текущий документ\n\n"
        "📝 Советы:\n"
        "• Задавайте конкретные вопросы для лучших ответов\n"
        "• Вы можете загрузить новый PDF в любое время\n"
        "• История беседы сохраняется до сброса\n\n"
        "Готовы начать? Отправьте PDF! 📚"
    )
    await update.message.reply_text(welcome_message)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /reset - очищает текущий документ и историю"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text(
            "ℹ️ Нет активного документа. Отправьте PDF для начала работы!"
        )
        return
    
    pdf_name = user_data[user_id].get("current_pdf", "документ")
    user_data.pop(user_id)
    
    await update.message.reply_text(
        f"✨ Успешно сброшено!\n\n"
        f"• Очищен: {pdf_name}\n"
        f"• История беседы удалена\n\n"
        "Отправьте новый PDF, когда будете готовы!"
    )

# ------------------------------------------------------------------------------
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# ------------------------------------------------------------------------------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик загрузки документов.
    Принимает PDF файлы, загружает их в ChatPDF и сохраняет для дальнейшего использования.
    """
    document = update.message.document
    file_name = document.file_name or "document.pdf"
    
    # Проверка формата файла
    if not file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "⚠️ Пожалуйста, отправьте PDF файл.\n\n"
            "Убедитесь, что файл имеет расширение .pdf"
        )
        return

    # Отправляем сообщение о начале обработки
    status_message = await update.message.reply_text(
        f"📤 Обработка: {file_name}\n\n"
        "Пожалуйста, подождите, пока я анализирую документ..."
    )
    
    # Загружаем файл локально
    file_id = document.file_id
    new_file = await context.bot.get_file(file_id)
    local_path = f"{update.effective_user.id}.pdf"
    await new_file.download_to_drive(local_path)

    try:
        # Загружаем PDF в ChatPDF
        source_id = upload_pdf_to_chatpdf(local_path)
        user_id = update.effective_user.id
        
        # Сохраняем информацию о документе
        user_data[user_id] = {
            "sourceId": source_id,
            "messages": [],
            "current_pdf": file_name
        }
        
        # Отправляем сообщение об успешной загрузке
        success_message = (
            f"✅ Успешно загружено: {file_name}\n\n"
            "Теперь вы можете:\n"
            "• Задавать любые вопросы по документу\n"
            "• Загрузить другой PDF для смены документа\n"
            "• Использовать /reset для очистки\n\n"
            "Что бы вы хотели узнать о вашем PDF? 🤔"
        )
        await status_message.edit_text(success_message)
        
    except Exception as e:
        # Обработка ошибок при загрузке
        error_message = (
            "❌ Извините, произошла ошибка при обработке PDF.\n\n"
            f"Детали ошибки: {str(e)}\n\n"
            "Попробуйте:\n"
            "• Проверить, не поврежден ли PDF\n"
            "• Убедиться, что файл не защищен паролем\n"
            "• Загрузить другой PDF"
        )
        await status_message.edit_text(error_message)
    finally:
        # Удаляем временный файл
        if os.path.exists(local_path):
            os.remove(local_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик текстовых сообщений.
    Отправляет вопросы к ChatPDF API и возвращает ответы.
    """
    user_id = update.effective_user.id
    
    # Проверяем, загружен ли PDF
    if user_id not in user_data:
        await update.message.reply_text(
            "📥 Пожалуйста, сначала отправьте PDF файл!\n\n"
            "Мне нужен документ, чтобы отвечать на вопросы."
        )
        return

    # Получаем вопрос и информацию о документе
    question = update.message.text.strip()
    source_id = user_data[user_id]["sourceId"]
    messages_history = user_data[user_id]["messages"]
    messages_history.append({"role": "user", "content": question})

    # Показываем индикатор набора текста
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        # Получаем ответ от ChatPDF
        response = ask_chatpdf(source_id, messages_history)
        answer = response.get("content", "Нет доступного ответа.")
        messages_history.append({"role": "assistant", "content": answer})
        
        # Форматируем и отправляем ответ
        formatted_answer = format_text(answer)
        await update.message.reply_text(
            formatted_answer,
            parse_mode="HTML",
            reply_markup=create_inline_keyboard()
        )
    except Exception as e:
        # Обработка ошибок при получении ответа
        error_message = (
            "❌ Извините, не удалось обработать ваш вопрос.\n\n"
            f"Ошибка: {str(e)}\n\n"
            "Попробуйте:\n"
            "• Переформулировать вопрос\n"
            "• Проверить подключение к интернету\n"
            "• Использовать /reset и загрузить PDF снова"
        )
        await update.message.reply_text(error_message)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "new_chat":
        # Очищаем данные пользователя
        if user_id in user_data:
            user_data.pop(user_id)
        await query.answer("Начинаем сначала! 🆕")
        await query.message.reply_text(
            "Готов к новому документу! 📚\n"
            "Отправьте PDF для начала работы."
        )
    elif query.data == "clear_history":
        if user_id in user_data:
            # Очищаем только историю сообщений
            user_data[user_id]["messages"] = []
            await query.answer("История очищена! 🧹")
            await query.message.reply_text(
                "История беседы очищена.\n"
                "Ваш PDF все еще загружен - задавайте вопросы!"
            )
        else:
            await query.answer("Нет активной сессии для очистки!")

# ------------------------------------------------------------------------------
# ИНИЦИАЛИЗАЦИЯ И ЗАПУСК БОТА
# ------------------------------------------------------------------------------

async def setup_commands(app) -> None:
    """Устанавливает команды бота"""
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("reset", "Очистить текущий документ и историю")
    ]
    await app.bot.set_my_commands(commands)

async def main_async() -> None:
    """Основная функция запуска бота"""
    print("🚀 Запуск PDF Чат Ассистента...")
    
    # Создаем приложение
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Устанавливаем команды
    await setup_commands(app)
    
    print("✨ Бот готов к обработке PDF!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main_async())

