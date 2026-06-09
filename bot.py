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
    "Идут технические работы.\n\n"
    "Мы переезжаем на новый сервер. Все ваши данные и подписки сохранены.\n\n"
    "Пожалуйста, загляните чуть позже 🙏"
)

LIVE_TEXT = (
    "👋 Бот и сайт теперь тут!\n\n"
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

    if os.environ.get("RELINK_BROADCAST") == "1" and not os.path.exists(".broadcast_done"):
        logger.info("Запуск автоматической рассылки всем пользователям...")
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL не указан, рассылка отменена.")
        else:
            try:
                import psycopg
                from psycopg.rows import dict_row
                with psycopg.connect(db_url, row_factory=dict_row) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT DISTINCT chat_id FROM (
                                SELECT chat_id FROM chat_users
                                UNION
                                SELECT chat_id FROM chat_settings
                            ) as combined
                        """)
                        users = cur.fetchall()
                        
                logger.info("Найдено %d пользователей для рассылки.", len(users))
                success_count = 0
                for user in users:
                    chat_id = user["chat_id"]
                    try:
                        await bot.send_message(
                            chat_id, 
                            LIVE_TEXT, 
                            reply_markup=LIVE_KEYBOARD, 
                            disable_web_page_preview=True
                        )
                        success_count += 1
                    except Exception as e:
                        logger.warning("Не удалось отправить %s: %s", chat_id, e)
                    await asyncio.sleep(0.05)
                
                logger.info("Рассылка завершена. Успешно: %d/%d", success_count, len(users))
                with open(".broadcast_done", "w", encoding="utf-8") as f:
                    f.write("Рассылка успешно выполнена!")
            except Exception as e:
                logger.error("Ошибка при рассылке: %s", e)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
