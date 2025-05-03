from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import asyncio
import os

# Получение токена бота из переменных окружения
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN )
dp = Dispatcher()

# Словарь для хранения курсов валют {валюта: курс}
currency_rates = {}

# Состояния для FSM (сохранение валюты)
class CurrencyStates(StatesGroup):
    name = State()
    rate = State()
    currency = State()
    amount = State()

# Обработчик команды /start
# Отправляет приветственное сообщение с описанием доступных команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для работы с курсами валют.\n"
        "Доступные команды:\n"
        "/save_currency - сохранить курс валюты\n"
        "/convert - конвертировать валюту в рубли"
    )

# Обработчик команды /save_currency
# Инициирует процесс сохранения курса валюты, переводит в состояние name
@dp.message(Command("save_currency"))
async def cmd_save_currency(message: Message, state: FSMContext):
    await message.answer("Введите название валюты (например, USD, EUR):")
    await state.set_state(CurrencyStates.name)

# Обработчик ввода названия валюты для сохранения
# Проверяет валидность введенного названия и переводит в состояние rate
@dp.message(CurrencyStates.name)
async def process_currency_name(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    
    # Проверка на валидность названия валюты
    if not currency_name.isalpha() or len(currency_name) != 3:
        await message.answer("Название валюты должно состоять из 3 букв. Попробуйте еще раз:")
        return
    
    await state.update_data(currency_name=currency_name)
    await message.answer(f"Введите курс {currency_name} к рублю (например, 75.5):")
    await state.set_state(CurrencyStates.rate)

# Обработчик ввода курса валюты
# Проверяет валидность введенного курса и сохраняет данные
@dp.message(CurrencyStates.rate)
async def process_currency_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
        if rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Курс должен быть положительным числом. Попробуйте еще раз:")
        return
    
    data = await state.get_data()
    currency_name = data['currency_name']
    currency_rates[currency_name] = rate
    
    await message.answer(f"Курс {currency_name} сохранен: 1 {currency_name} = {rate} RUB")
    await state.clear()

# Обработчик команды /convert
# Инициирует процесс конвертации валюты, переводит в состояние currency
@dp.message(Command("convert"))
async def cmd_convert(message: Message, state: FSMContext):
    if not currency_rates:
        await message.answer("Нет сохраненных курсов валют. Сначала сохраните курс с помощью /save_currency")
        return
    
    await message.answer(
        "Введите название валюты для конвертации (доступные валюты: " 
        + ", ".join(currency_rates.keys()) + "):"
    )
    await state.set_state(CurrencyStates.currency)

# Обработчик ввода валюты для конвертации
# Проверяет наличие валюты в списке и переводит в состояние amount
@dp.message(CurrencyStates.currency)
async def process_convert_currency(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    
    if currency_name not in currency_rates:
        await message.answer(
            "Такой валюты нет в списке. Доступные валюты: " 
            + ", ".join(currency_rates.keys()) + "\nПопробуйте еще раз:"
        )
        return
    
    await state.update_data(convert_currency=currency_name)
    await message.answer(f"Введите сумму в {currency_name} для конвертации в рубли:")
    await state.set_state(CurrencyStates.amount)

# Обработчик ввода суммы для конвертации
# Выполняет конвертацию и выводит результат
@dp.message(CurrencyStates.amount)
async def process_convert_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом. Попробуйте еще раз:")
        return
    
    data = await state.get_data()
    currency_name = data['convert_currency']
    rate = currency_rates[currency_name]
    result = amount * rate
    
    await message.answer(f"{amount} {currency_name} = {result:.2f} RUB")
    await state.clear()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())