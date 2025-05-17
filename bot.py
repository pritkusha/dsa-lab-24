import os
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from decimal import Decimal, InvalidOperation
import asyncio
import psycopg2
from psycopg2 import sql
import requests

# Настройки бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()

# URL микросервисов
CURRENCY_MANAGER_URL = 'http://localhost:5001'
DATA_MANAGER_URL = 'http://localhost:5002'

# Состояния для FSM
class CurrencyStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_rate = State()
    waiting_for_amount = State()
    waiting_for_new_rate = State()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = [
        [types.KeyboardButton(text="/manage_currency")],
        [types.KeyboardButton(text="/get_currencies")],
        [types.KeyboardButton(text="/convert")]
    ]
    reply_markup = types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите команду"
    )
    await message.answer("Выберите команду:", reply_markup=reply_markup)

# Команда /manage_currency
@dp.message(Command("manage_currency"))
async def manage_currency(message: Message):
    buttons = [
        [InlineKeyboardButton(text="Добавить валюту", callback_data="add_currency")],
        [InlineKeyboardButton(text="Удалить валюту", callback_data="delete_currency")],
        [InlineKeyboardButton(text="Изменить курс валюты", callback_data="update_currency")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Обработка кнопок manage_currency
@dp.callback_query(lambda c: c.data in ["add_currency", "delete_currency", "update_currency"])
async def process_currency_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    await state.update_data(action=action)
    
    if action == "add_currency":
        await state.set_state(CurrencyStates.waiting_for_name)
        await callback.message.answer("Введите название валюты:")
    elif action == "delete_currency":
        await state.set_state(CurrencyStates.waiting_for_name)
        await callback.message.answer("Введите название валюты для удаления:")
    elif action == "update_currency":
        await state.set_state(CurrencyStates.waiting_for_name)
        await callback.message.answer("Введите название валюты для изменения курса:")
    
    await callback.answer()

# Обработка ввода названия валюты
@dp.message(CurrencyStates.waiting_for_name)
async def process_currency_name(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get('action')
    currency_name = message.text
    
    await state.update_data(currency_name=currency_name)
    
    if action == "delete_currency":
        response = requests.post(f"{CURRENCY_MANAGER_URL}/delete", json={'name': currency_name})
        if response.status_code == 200:
            await message.answer(f"Валюта {currency_name} успешно удалена")
        else:
            await message.answer(f"Ошибка: {response.json().get('error')}")
        await state.clear()
    elif action == "add_currency":
        await state.set_state(CurrencyStates.waiting_for_rate)
        await message.answer("Введите курс к рублю:")
    elif action == "update_currency":
        await state.set_state(CurrencyStates.waiting_for_new_rate)
        await message.answer("Введите новый курс к рублю:")

# Обработка ввода курса для добавления валюты
@dp.message(CurrencyStates.waiting_for_rate)
async def process_currency_rate(message: Message, state: FSMContext):
    try:
        rate = Decimal(message.text)
        data = await state.get_data()
        currency_name = data['currency_name']
        
        response = requests.post(f"{CURRENCY_MANAGER_URL}/load", json={'name': currency_name, 'rate': float(rate)})
        if response.status_code == 200:
            await message.answer(f"Валюта {currency_name} успешно добавлена")
        else:
            await message.answer(f"Ошибка: {response.json().get('error')}")
        
        await state.clear()
    except (ValueError, InvalidOperation):
        await message.answer("Пожалуйста, введите число для курса")

# Обработка ввода нового курса для обновления
@dp.message(CurrencyStates.waiting_for_new_rate)
async def process_new_rate(message: Message, state: FSMContext):
    try:
        new_rate = Decimal(message.text)
        data = await state.get_data()
        currency_name = data['currency_name']
        
        response = requests.post(f"{CURRENCY_MANAGER_URL}/update_currency", json={'name': currency_name, 'rate': float(new_rate)})
        if response.status_code == 200:
            await message.answer(f"Курс валюты {currency_name} успешно обновлен")
        else:
            await message.answer(f"Ошибка: {response.json().get('error')}")
        
        await state.clear()
    except (ValueError, InvalidOperation):
        await message.answer("Пожалуйста, введите число для курса")

# Команда /get_currencies
@dp.message(Command("get_currencies"))
async def get_currencies(message: Message):
    response = requests.get(f"{DATA_MANAGER_URL}/currencies")
    if response.status_code == 200:
        currencies = response.json()
        if currencies:
            message_text = "Список валют:\n"
            for currency in currencies:
                message_text += f"{currency['currency_name']}: {currency['rate']}\n"
            await message.answer(message_text)
        else:
            await message.answer("Валюты не найдены")
    else:
        await message.answer("Ошибка при получении списка валют")

# Команда /convert
@dp.message(Command("convert"))
async def convert_currency(message: Message, state: FSMContext):
    await state.set_state(CurrencyStates.waiting_for_name)
    await state.update_data(action="convert")
    await message.answer("Введите название валюты:")

# Обработка конвертации - ввод суммы
@dp.message(CurrencyStates.waiting_for_amount)
async def process_convert_amount(message: Message, state: FSMContext):
    try:
        amount = Decimal(message.text)
        data = await state.get_data()
        currency_name = data['currency_name']
        
        response = requests.get(f"{DATA_MANAGER_URL}/convert", params={'currency': currency_name, 'amount': float(amount)})
        if response.status_code == 200:
            converted_amount = response.json().get('converted_amount')
            await message.answer(f"{amount} {currency_name} = {converted_amount} RUB")
        else:
            await message.answer(f"Ошибка: {response.json().get('error')}")
        
        await state.clear()
    except (ValueError, InvalidOperation):
        await message.answer("Пожалуйста, введите число для суммы")

# Обработка конвертации - ввод валюты
@dp.message(CurrencyStates.waiting_for_name)
async def process_convert_name(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get('action') == "convert":
        await state.update_data(currency_name=message.text)
        await state.set_state(CurrencyStates.waiting_for_amount)
        await message.answer("Введите сумму для конвертации:")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())