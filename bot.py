import asyncio
from typing import Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from config import BOT_TOKEN, OWNER_CHAT_ID, SCAN_INTERVAL_SECONDS, DEFAULT_KEYWORDS
from scraper import Order, find_new_orders_for_all_sites
from storage import add_site, get_sites, remove_site


bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# простейшее состояние для добавления/удаления сайтов по кнопкам
pending_action: Dict[int, str] = {}


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔍 Сканировать сейчас"),
                KeyboardButton(text="📃 Список сайтов"),
            ],
            [
                KeyboardButton(text="➕ Добавить сайт"),
                KeyboardButton(text="➖ Удалить сайт"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите сообщение или выберите действие…",
    )


def build_order_keyboard(order: Order) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть заказ", url=order.url)],
        ]
    )


async def send_orders(orders: List[Order]) -> None:
    if not orders:
        return

    for order in orders:
        text = (
            f"<b>Новый заказ с площадки:</b> {order.source}\n\n"
            f"<b>Заголовок:</b> {order.title}\n\n"
            f"<b>Описание (фрагмент):</b>\n{order.snippet}"
        )
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=text,
            reply_markup=build_order_keyboard(order),
            disable_web_page_preview=True,
        )


async def periodic_scan() -> None:
    while True:
        sites = get_sites()
        if sites:
            orders = await find_new_orders_for_all_sites(sites, keywords=DEFAULT_KEYWORDS)
            await send_orders(orders)
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.from_user.id != OWNER_CHAT_ID:
        await message.answer("Этот бот предназначен только для владельца.")
        return

    await message.answer(
        "Привет! Я бот для сбора заказов с фриланс‑площадок.\n\n"
        "Используйте кнопки под строкой ввода, чтобы:\n"
        "🔍 запустить поиск заказов\n"
        "📃 посмотреть список сайтов\n"
        "➕ добавить сайт\n"
        "➖ удалить сайт\n\n"
        f"Периодический скан: каждые {SCAN_INTERVAL_SECONDS} секунд.",
        reply_markup=build_main_keyboard(),
    )


@dp.message(Command("whoami"))
async def cmd_whoami(message: Message) -> None:
    await message.answer(f"Ваш chat_id: <code>{message.chat.id}</code>")


@dp.message(F.text == "📃 Список сайтов")
async def handle_list_sites(message: Message) -> None:
    if message.from_user.id != OWNER_CHAT_ID:
        return

    sites = get_sites()
    if not sites:
        await message.answer("Список сайтов пуст. Добавьте сайт кнопкой «➕ Добавить сайт».")
        return

    text = "<b>Сайты под мониторингом:</b>\n" + "\n".join(f"- {s}" for s in sites)
    await message.answer(text)


@dp.message(F.text == "🔍 Сканировать сейчас")
async def handle_scan_now(message: Message) -> None:
    if message.from_user.id != OWNER_CHAT_ID:
        return

    sites = get_sites()
    if not sites:
        await message.answer("Список сайтов пуст. Сначала добавьте хотя бы один сайт.")
        return

    await message.answer("Ищу новые заказы, подождите...")
    orders = await find_new_orders_for_all_sites(sites, keywords=DEFAULT_KEYWORDS)
    if not orders:
        await message.answer("Новых заказов не найдено.")
        return

    await send_orders(orders)


@dp.message(F.text == "➕ Добавить сайт")
async def handle_add_site_button(message: Message) -> None:
    if message.from_user.id != OWNER_CHAT_ID:
        return

    pending_action[message.from_user.id] = "add"
    await message.answer(
        "Отправьте ссылку на страницу с заказами, которую нужно добавить.\n"
        "Например: https://kwork.ru/projects или https://www.fl.ru/projects/",
        reply_markup=build_main_keyboard(),
    )


@dp.message(F.text == "➖ Удалить сайт")
async def handle_remove_site_button(message: Message) -> None:
    if message.from_user.id != OWNER_CHAT_ID:
        return

    pending_action[message.from_user.id] = "remove"
    await message.answer(
        "Отправьте точную ссылку сайта, который нужно убрать из мониторинга.",
        reply_markup=build_main_keyboard(),
    )


@dp.message(F.text.regexp(r"^https?://"))
async def handle_url_input(message: Message) -> None:
    if message.from_user.id != OWNER_CHAT_ID:
        return

    action = pending_action.get(message.from_user.id)
    url = message.text.strip()

    if action == "add":
        if add_site(url):
            await message.answer(f"Сайт добавлен в мониторинг:\n{url}", reply_markup=build_main_keyboard())
        else:
            await message.answer("Такой сайт уже есть или URL некорректный.", reply_markup=build_main_keyboard())
        pending_action.pop(message.from_user.id, None)
        return

    if action == "remove":
        if remove_site(url):
            await message.answer(f"Сайт удалён из мониторинга:\n{url}", reply_markup=build_main_keyboard())
        else:
            await message.answer("Такого сайта в списке нет.", reply_markup=build_main_keyboard())
        pending_action.pop(message.from_user.id, None)
        return

    # если никакого ожидания нет — просто подскажем про кнопки
    await message.answer(
        "Если хотите добавить или удалить сайт, сначала выберите соответствующую кнопку под строкой ввода.",
        reply_markup=build_main_keyboard(),
    )


@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


async def main() -> None:
    asyncio.create_task(periodic_scan())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

