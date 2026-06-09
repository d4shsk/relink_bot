import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("relink_bot")

BOT_USERNAME = "anywai_bot"
SITE_URL = "https://chat.anywai.ru/"
BOT_URL = f"https://t.me/{BOT_USERNAME}"

# Два режима работы:
#   maintenance — идут техработы/миграция, ссылки на нового бота НЕ показываем.
#   live        — переезд завершён, показываем полное сообщение со ссылками.
# Управляется переменной окружения RELINK_MODE. По умолчанию — безопасный
# режим техработ, чтобы случайно не увести пользователей до завершения миграции.
MODE_MAINTENANCE = "maintenance"
MODE_LIVE = "live"

MAINTENANCE_TEXT = (
    "� Идут технические работы.\n\n"
    "Мы переезжаем на новый сервер. Все ваши данные и подписки сохранены.\n\n"
    "Пожалуйста, загляните чуть позже 🙏"
)

LIVE_TEXT = (
    "�👋 Бот и сайт теперь тут!\n\n"
    "Все ваши данные и подписки сохранены.\n\n"
    "Переходите по ссылкам ниже 👇"
)

# Кнопки со ссылками показываются только в режиме live.
LIVE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=f"🤖 @{BOT_USERNAME}", url=BOT_URL)],
        [InlineKeyboardButton(text="🌐 chat.anywai.ru", url=SITE_URL)],
    ]
)


def get_mode() -> str:
    """Текущий режим из окружения, по умолчанию — техработы."""
    mode = os.environ.get("RELINK_MODE", MODE_MAINTENANCE).strip().lower()
    if mode not in (MODE_MAINTENANCE, MODE_LIVE):
        logger.warning(
            "Неизвестный RELINK_MODE=%r, использую %r.", mode, MODE_MAINTENANCE
        )
        return MODE_MAINTENANCE
    return mode


dispatcher = Dispatcher()


@dispatcher.message()
async def handle_any_message(message: Message) -> None:
    """Reply to ANY incoming message according to the current mode."""
    if get_mode() == MODE_LIVE:
        await message.answer(
            LIVE_TEXT,
            reply_markup=LIVE_KEYBOARD,
            disable_web_page_preview=True,
        )
    else:
        await message.answer(
            MAINTENANCE_TEXT,
            disable_web_page_preview=True,
        )


async def run() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Не найден TELEGRAM_TOKEN в переменных окружения.")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logger.info("Запуск relink-бота в режиме %r...", get_mode())
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
