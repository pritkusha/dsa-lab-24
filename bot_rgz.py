import os
import asyncio
import requests
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from decimal import Decimal, InvalidOperation
import psycopg2

# Бот и диспетчер
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Подключение к БД
conn = psycopg2.connect(
    dbname="finance_db",
    user="postgres",
    password="postgres",
    host="127.0.0.1",
    port="5432"
)


conn.autocommit = True
cursor = conn.cursor()

# FSM состояния
class Registration(StatesGroup):
    waiting_for_login = State()

class OperationFSM(StatesGroup):
    waiting_for_type = State()
    waiting_for_amount = State()
    waiting_for_date = State()
    waiting_for_category = State()

class CategoryFSM(StatesGroup):
    waiting_for_name = State()

# Проверка регистрации
def is_registered(chat_id):
    cursor.execute("SELECT 1 FROM users WHERE chat_id = %s", (chat_id,))
    return cursor.fetchone() is not None

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот для учета финансовых операций.\n"
        "Доступные команды:\n"
        "/reg - регистрация\n"
        "/add_category - добавить категорию\n"
        "/add_operation - добавить операцию\n"
        "/operations - просмотр операций"
    )

# Команда /reg — регистрация
@dp.message(Command("reg"))
async def cmd_reg(message: types.Message, state: FSMContext):
    chat_id = message.chat.id

    # Проверка, зарегистрирован ли пользователь
    cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
    if cursor.fetchone():
        await message.answer("Вы уже зарегистрированы.")
        return

    await message.answer("Введите ваш логин:")
    await state.set_state(Registration.waiting_for_login)

# Обработка логина
@dp.message(Registration.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    login = message.text.strip()
    chat_id = message.chat.id

    # Сохраняем логин и chat_id
    cursor.execute("INSERT INTO users (chat_id, name) VALUES (%s, %s)", (chat_id, login))
    conn.commit()

    await message.answer("Вы успешно зарегистрированы!", reply_markup=ReplyKeyboardRemove())
    await state.clear()

# /add_category
@dp.message(Command("add_category"))
async def add_category(message: Message, state: FSMContext):
    if not is_registered(message.chat.id):
        await message.answer("Сначала зарегистрируйтесь с помощью /reg")
        return
    await message.answer("Введите название новой категории:")
    await state.set_state(CategoryFSM.waiting_for_name)

@dp.message(CategoryFSM.waiting_for_name)
async def save_category(message: Message, state: FSMContext):
    cursor.execute("INSERT INTO categories (name, chat_id) VALUES (%s, %s)", (message.text, message.chat.id))
    await message.answer("Категория успешно добавлена!")
    await state.clear()

# /add_operation
@dp.message(Command("add_operation"))
async def start_add_operation(message: Message, state: FSMContext):
    if not is_registered(message.chat.id):
        await message.answer("Сначала зарегистрируйтесь с помощью /reg")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="РАСХОД", callback_data="РАСХОД")],
        [InlineKeyboardButton(text="ДОХОД", callback_data="ДОХОД")]
    ])
    await message.answer("Выберите тип операции:", reply_markup=keyboard)
    await state.set_state(OperationFSM.waiting_for_type)

@dp.callback_query(OperationFSM.waiting_for_type)
async def set_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(type_operation=callback.data)
    await callback.message.answer("Введите сумму операции в рублях:", reply_markup=ReplyKeyboardRemove())
    await callback.answer()
    await state.set_state(OperationFSM.waiting_for_amount)

@dp.message(OperationFSM.waiting_for_amount)
async def set_amount(message: Message, state: FSMContext):
    try:
        amount = Decimal(message.text)
    except InvalidOperation:
        await message.answer("Введите корректное число.")
        return
    await state.update_data(sum=amount)
    await message.answer("Введите дату операции в формате YYYY-MM-DD:")
    await state.set_state(OperationFSM.waiting_for_date)

@dp.message(OperationFSM.waiting_for_date)
async def set_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer("Введите категорию операции:")
    await state.set_state(OperationFSM.waiting_for_category)

@dp.message(OperationFSM.waiting_for_category)
async def set_category(message: Message, state: FSMContext):
    category = message.text
    cursor.execute("SELECT id FROM categories WHERE name = %s AND chat_id = %s", (category, message.chat.id))
    result = cursor.fetchone()
    if not result:
        await message.answer("Такой категории нет. Добавьте через /add_category.")
        return
    cat_id = result[0]
    data = await state.get_data()
    cursor.execute(
        "INSERT INTO operations (date, sum, chat_id, type_operation, category_id) VALUES (%s, %s, %s, %s, %s)",
        (data["date"], data["sum"], message.chat.id, data["type_operation"], cat_id)
    )
    await message.answer("Операция успешно добавлена.")
    await state.clear()

# /operations
@dp.message(Command("operations"))
async def get_operations(message: Message):
    if not is_registered(message.chat.id):
        await message.answer("Сначала зарегистрируйтесь.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="RUB", callback_data="RUB")],
        [InlineKeyboardButton(text="EUR", callback_data="EUR")],
        [InlineKeyboardButton(text="USD", callback_data="USD")],
    ])
    await message.answer("Выберите валюту:", reply_markup=keyboard)

@dp.callback_query()
async def handle_currency(callback: types.CallbackQuery):
    currency = callback.data

    rate = 1.0
    if currency in ["USD", "EUR"]:
        try:
            response = requests.get("http://127.0.0.1:5001/rate", params={"currency": currency})
            if response.status_code != 200:
                await callback.message.answer("Ошибка получения курса валют.")
                await callback.answer()
                return
            rate_data = response.json()
            rate = rate_data.get("rate", 1.0)
        except Exception:
            await callback.message.answer("Не удалось подключиться к серверу курса валют.")
            await callback.answer()
            return

    # Получаем операции пользователя
    cursor.execute("SELECT date, sum, type_operation FROM operations WHERE chat_id = %s", (callback.message.chat.id,))
    records = cursor.fetchall()

    if not records:
        await callback.message.answer("У вас пока нет ни одной операции.")
        await callback.answer()
        return

    total_income = 0.0
    total_expense = 0.0
    text = f"<b>Операции в {currency}:</b>\n\n"

    for date, amount, op_type in records:
        converted = round(float(amount) / rate, 2)
        text += f"{date} | {converted} {currency} | {op_type}\n"
        if op_type == "ДОХОД":
            total_income += float(amount)
        elif op_type == "РАСХОД":
            total_expense += float(amount)

    income_converted = round(total_income / rate, 2)
    expense_converted = round(total_expense / rate, 2)
    balance_converted = round((total_income - total_expense) / rate, 2)

    text += f"\n<b>Сводка:</b>\n"
    text += f"Доходы: {income_converted} {currency}\n"
    text += f"Расходы: {expense_converted} {currency}\n"
    text += f"<b>Баланс: {balance_converted} {currency}</b>"

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
