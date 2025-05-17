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

# Раздел I. Создание базы данных

# Подключение к базе данных
def create_connection():
    try:
        conn = psycopg2.connect(
            dbname="lab6db",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None

# Создание таблиц
def create_tables():
    conn = create_connection()
    if conn is None:
        return
    
    try:
        with conn.cursor() as cursor:
            # Создание таблицы currencies
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS currencies (
                    id SERIAL PRIMARY KEY,
                    currency_name VARCHAR(50) UNIQUE NOT NULL,
                    rate NUMERIC(10, 4) NOT NULL
                )
            """)
            
            # Создание таблицы admins
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    chat_id VARCHAR(50) UNIQUE NOT NULL
                )
            """)
            
            conn.commit()
            print("Таблицы успешно созданы")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
    finally:
        if conn:
            conn.close()

create_tables()

# Раздел II. Разработка бота

# Получение токена бота из переменных окружения
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Состояния для FSM
class CurrencyStates(StatesGroup):
    name = State()
    rate = State()
    currency = State()
    amount = State()
    delete_currency = State()
    edit_currency = State()
    edit_rate = State()

# Проверка администратора
async def is_admin(chat_id: str) -> bool:
    conn = create_connection()
    if conn is None:
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM admins WHERE chat_id = %s", (str(chat_id),))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"Ошибка при проверке администратора: {e}")
        return False
    finally:
        if conn:
            conn.close()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if await is_admin(message.chat.id):
        await message.answer(
            "Привет! Я бот для работы с курсами валют.\n"
            "Доступные команды:\n"
            "/manage_currency - управление валютами (только для админов)\n"
            "/get_currencies - просмотр курсов валют\n"
            "/convert - конвертировать валюту в рубли"
        )
    else:
        await message.answer(
            "Привет! Я бот для работы с курсами валют.\n"
            "Доступные команды:\n"
            "/get_currencies - просмотр курсов валют\n"
            "/convert - конвертировать валюту в рубли"
        )

# Обработчик команды /manage_currency (только для админов)
@dp.message(Command("manage_currency"))
async def cmd_manage_currency(message: Message, state: FSMContext):
    if not await is_admin(message.chat.id):
        await message.answer("Нет доступа к команде")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Добавить валюту", callback_data="add_currency"),
            InlineKeyboardButton(text="Удалить валюту", callback_data="delete_currency"),
            InlineKeyboardButton(text="Изменить курс", callback_data="edit_currency")
        ]
    ])
    
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Обработчик кнопок управления валютами
@dp.callback_query()
async def process_currency_actions(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "add_currency":
        await callback.message.answer("Введите название валюты (например, USD, EUR):")
        await state.set_state(CurrencyStates.name)
    elif callback.data == "delete_currency":
        await callback.message.answer("Введите название валюты для удаления:")
        await state.set_state(CurrencyStates.delete_currency)
    elif callback.data == "edit_currency":
        await callback.message.answer("Введите название валюты для изменения курса:")
        await state.set_state(CurrencyStates.edit_currency)
    
    await callback.answer()

# Обработчик добавления валюты - название
@dp.message(CurrencyStates.name)
async def process_add_currency_name(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    
    # Проверка на валидность названия валюты
    if not currency_name.isalpha() or len(currency_name) != 3:
        await message.answer("Название валюты должно состоять из 3 букв. Попробуйте еще раз:")
        return
    
    # Проверка на существование валюты
    conn = create_connection()
    if conn is None:
        await state.clear()
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM currencies WHERE currency_name = %s", (currency_name,))
            if cursor.fetchone() is not None:
                await message.answer("Данная валюта уже существует")
                await state.clear()
                return
            
            await state.update_data(currency_name=currency_name)
            await message.answer(f"Введите курс {currency_name} к рублю (например, 75.5):")
            await state.set_state(CurrencyStates.rate)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()
    finally:
        if conn:
            conn.close()

# Обработчик добавления валюты - курс
@dp.message(CurrencyStates.rate)
async def process_add_currency_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
        if rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Курс должен быть положительным числом. Попробуйте еще раз:")
        return
    
    data = await state.get_data()
    currency_name = data['currency_name']
    
    conn = create_connection()
    if conn is None:
        await state.clear()
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO currencies (currency_name, rate) VALUES (%s, %s)",
                (currency_name, rate)
            )
            conn.commit()
            await message.answer(f"Валюта {currency_name} успешно добавлена с курсом {rate} RUB")
    except Exception as e:
        await message.answer(f"Ошибка при добавлении валюты: {e}")
    finally:
        if conn:
            conn.close()
        await state.clear()

# Обработчик удаления валюты
@dp.message(CurrencyStates.delete_currency)
async def process_delete_currency(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    
    conn = create_connection()
    if conn is None:
        await state.clear()
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM currencies WHERE currency_name = %s", (currency_name,))
            if cursor.rowcount == 0:
                await message.answer(f"Валюта {currency_name} не найдена")
            else:
                conn.commit()
                await message.answer(f"Валюта {currency_name} успешно удалена")
    except Exception as e:
        await message.answer(f"Ошибка при удалении валюты: {e}")
    finally:
        if conn:
            conn.close()
        await state.clear()

# Обработчик изменения курса - выбор валюты
@dp.message(CurrencyStates.edit_currency)
async def process_edit_currency(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    
    conn = create_connection()
    if conn is None:
        await state.clear()
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM currencies WHERE currency_name = %s", (currency_name,))
            if cursor.fetchone() is None:
                await message.answer(f"Валюта {currency_name} не найдена")
                await state.clear()
                return
            
            await state.update_data(edit_currency=currency_name)
            await message.answer(f"Введите новый курс для {currency_name}:")
            await state.set_state(CurrencyStates.edit_rate)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()
    finally:
        if conn:
            conn.close()

# Обработчик изменения курса - новый курс
@dp.message(CurrencyStates.edit_rate)
async def process_edit_rate(message: Message, state: FSMContext):
    try:
        new_rate = float(message.text.replace(",", "."))
        if new_rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Курс должен быть положительным числом. Попробуйте еще раз:")
        return
    
    data = await state.get_data()
    currency_name = data['edit_currency']
    
    conn = create_connection()
    if conn is None:
        await state.clear()
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE currencies SET rate = %s WHERE currency_name = %s",
                (new_rate, currency_name)
            )
            conn.commit()
            await message.answer(f"Курс {currency_name} успешно изменен на {new_rate} RUB")
    except Exception as e:
        await message.answer(f"Ошибка при изменении курса: {e}")
    finally:
        if conn:
            conn.close()
        await state.clear()

# Обработчик команды /get_currencies
@dp.message(Command("get_currencies"))
async def cmd_get_currencies(message: Message):
    conn = create_connection()
    if conn is None:
        await message.answer("Ошибка подключения к базе данных")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT currency_name, rate FROM currencies ORDER BY currency_name")
            currencies = cursor.fetchall()
            
            if not currencies:
                await message.answer("В базе данных нет сохраненных валют")
                return
            
            response = "Текущие курсы валют:\n"
            for currency in currencies:
                response += f"{currency[0]}: {currency[1]} RUB\n"
            
            await message.answer(response)
    except Exception as e:
        await message.answer(f"Ошибка при получении курсов валют: {e}")
    finally:
        if conn:
            conn.close()

# Обработчик команды /convert - выбор валюты
@dp.message(Command("convert"))
async def cmd_convert(message: Message, state: FSMContext):
    conn = create_connection()
    if conn is None:
        await message.answer("Ошибка подключения к базе данных")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT currency_name FROM currencies")
            currencies = cursor.fetchall()
            
            if not currencies:
                await message.answer("В базе данных нет сохраненных валют")
                return
            
            await message.answer(
                "Введите название валюты для конвертации (доступные: " +
                ", ".join([curr[0] for curr in currencies]) + "):"
            )
            await state.set_state(CurrencyStates.currency)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    finally:
        if conn:
            conn.close()

# Обработчик конвертации - выбор валюты
@dp.message(CurrencyStates.currency)
async def process_convert_currency(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    
    conn = create_connection()
    if conn is None:
        await state.clear()
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT rate FROM currencies WHERE currency_name = %s", (currency_name,))
            rate = cursor.fetchone()
            
            if rate is None:
                await message.answer(
                    "Такой валюты нет в списке. Введите название еще раз или используйте /get_currencies для просмотра доступных валют:"
                )
                return
            
            await state.update_data(convert_currency=currency_name, convert_rate=rate[0])
            await message.answer(f"Введите сумму в {currency_name} для конвертации в рубли:")
            await state.set_state(CurrencyStates.amount)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()
    finally:
        if conn:
            conn.close()

# Обработчик конвертации - ввод суммы
@dp.message(CurrencyStates.amount)
async def process_convert_amount(message: Message, state: FSMContext):
    try:
        # Преобразуем ввод в Decimal для точных вычислений
        amount = Decimal(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
        
        data = await state.get_data()
        rate = data['convert_rate']  # Предполагаем, что rate уже Decimal
        
        # Умножаем Decimal на Decimal
        result = amount * rate
        
        await message.answer(
            f"{amount} {data['convert_currency']} = {result:.2f} RUB",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        
    except (ValueError, InvalidOperation):
        await message.answer("Введите корректную сумму (например: 100 или 50.5):")
    except Exception as e:
        await message.answer(f"Ошибка конвертации: {e}")
        await state.clear()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())