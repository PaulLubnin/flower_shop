import asyncio
import os
from datetime import datetime
from itertools import cycle

import phonenumbers
from aiogram import Bot, Dispatcher
from aiogram import executor
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from django.core.management import BaseCommand
from dotenv import load_dotenv

from bot.models import User, Flower, Order, Courier

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

events = ['День рождение', 'Свадьба', '8 марта', 'Рождение ребенка']

budgets = {
    'До 1000р': 1000,
    'До 5000р': 5000,
    'До 10000р': 10000,
    'Более 10000р': 10001
}


# other functions
def get_valid_phone(input_number: str):
    try:
        parse_number = phonenumbers.parse(input_number, "RU")
        national_number = phonenumbers.format_number(parse_number, phonenumbers.PhoneNumberFormat.E164)
        if phonenumbers.is_valid_number(parse_number):
            return national_number
    except phonenumbers.NumberParseException:
        print("Номер введен не верно, введите номер в формате \"+79876665544")


def get_filter_flower(price=None, event=None):
    flower_catalog = dict()
    flowers = Flower.objects.filter(price__lte=price, category=event)
    if price >= 10001:
        flowers = Flower.objects.filter(price__gte=price, category=event)

    for flower_number, flower_content in enumerate(flowers):
        flower_catalog[f'flower-{flower_number}'] = {
            'flower_id': flower_content.id,
            'filepath': flower_content.image,
            'caption': flower_content.description,
            'price': flower_content.price,
            'event': event
        }
    return flower_catalog


# keyboards
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    for event in events:
        keyboard.insert(event)
    return keyboard


def get_inline_keyboard(next_bouquet):
    order_button = InlineKeyboardButton(f'Заказать {next_bouquet[0]}', callback_data=next_bouquet[0])
    next_btn = InlineKeyboardButton(text="Следующий букет", callback_data="Следующий букет")
    consultation = InlineKeyboardButton(text="Свой вариант/консультация", callback_data="консультация")
    inline_keyboard = InlineKeyboardMarkup(row_width=2).add(order_button, next_btn, consultation)
    return inline_keyboard


# States
class Global(StatesGroup):
    event = State()
    budget = State()
    bouquet = State()
    person_data = State()
    registration_name = State()
    registration_phonenumber = State()
    cancel = State()
    address_street = State()
    address_number_house = State()
    address_number_flat = State()
    address_number_driveway = State()


class Command(BaseCommand):
    help = 'Запуск чат-бота'
    flower_dict_cycle = dict()
    flower_dict = dict()

    def handle(self, *args, **options):
        bot = Bot(BOT_TOKEN, parse_mode='HTML')
        storage = MemoryStorage()
        dp = Dispatcher(bot, storage=storage)

        async def on_startup(dp):
            await set_default_commands(dp)
            print("Бот запущен!")

        async def set_default_commands(dp):
            await dp.bot.set_my_commands(
                [
                    types.BotCommand('start', 'Запустить бота'),
                ]
            )

        @dp.message_handler(commands="start", state="*")
        async def flower_start(message: types.Message):
            user, created_user = User.objects.get_or_create(chat_id=message.chat.id)
            print(user, created_user)
            await message.answer("<b>Добро пожаловать! Вас приветствует бот для заказа букетов\n"
                                 "К какому событию готовимся? Выберите один из вариантов</b>",
                                 reply_markup=get_main_keyboard())
            await Global.event.set()

        @dp.message_handler(state=Global.event)
        async def get_event(message: types.Message, state: FSMContext):
            await state.update_data(chosen_event=message.text)
            await state.update_data(user_id=message.from_user.id)
            keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
            for description, budget in budgets.items():
                keyboard.insert(description)
            await message.answer("<b>На какой бюджет расчитываем?</b>",
                                 reply_markup=keyboard)

            await Global.budget.set()

        @dp.message_handler(state=Global.budget)
        async def get_budget(message: types.Message, state: FSMContext):
            await state.update_data(chosen_price=budgets[message.text])
            await message.answer("<b>Теперь выберем букет</b>")
            user_data = await state.get_data()
            global flower_dict_cycle
            global flower_dict
            flower_dict = get_filter_flower(price=user_data['chosen_price'], event=user_data['chosen_event'])
            flower_dict_cycle = cycle(flower_dict.items())
            next_bouquet = next(flower_dict_cycle)
            await bot.send_photo(message.from_user.id, photo=open(f'{dict(next_bouquet[1])["filepath"]}', 'rb'),
                                 caption=f'{dict(next_bouquet[1])["caption"]},'
                                         f' цена: {dict(next_bouquet[1])["price"]}',
                                 reply_markup=get_inline_keyboard(next_bouquet))
            await Global.bouquet.set()

        @dp.callback_query_handler(text="Следующий букет", state=Global.bouquet)
        async def get_next(message: types.Message):
            global flower_dict_cycle
            next_bouquet = next(flower_dict_cycle)
            await bot.send_photo(message.from_user.id, photo=open(f'{dict(next_bouquet[1])["filepath"]}', 'rb'),
                                 caption=f'{dict(next_bouquet[1])["caption"]},'
                                         f' цена: {dict(next_bouquet[1])["price"]}',
                                 reply_markup=get_inline_keyboard(next_bouquet))
            await Global.bouquet.set()

        @dp.callback_query_handler(text="консультация", state=Global.bouquet)
        async def get_access_with_consult(callback: types.CallbackQuery, state: FSMContext) -> None:
            await state.update_data(chosen_bouquet=callback.data)
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add("Согласен", "Не согласен")
            user = User.objects.get(chat_id=callback['from'].id)
            if user.access:
                await callback.message.answer(
                    'Введите своё имя и фамилию:',
                    reply_markup=types.ReplyKeyboardRemove()
                )
                await Global.registration_name.set()
            else:
                await callback.message.answer(
                    "<b>Ваша заявка будет передана флористу, для обсуждения деталей вам требуется "
                    "зарегистрироваться. "
                    "Даю согласия на обработку персональных данных?</b>", reply_markup=keyboard)
                await Global.person_data.set()

        @dp.callback_query_handler(lambda callback_query: callback_query, state=Global.bouquet)
        async def get_access(callback: types.CallbackQuery, state: FSMContext) -> None:

            global flower_dict
            print(callback['from'].id)
            user = User.objects.get(chat_id=callback['from'].id)
            await state.update_data(chosen_bouquet=callback.data)
            await state.update_data(bouquet_photo_id=callback.message["photo"][0]["file_id"])
            await state.update_data(bouquet_price=flower_dict[callback.data]['price'])
            await state.update_data(bouquet_id=flower_dict[callback.data]['flower_id'])
            if user.access:
                await callback.message.answer(
                    'Введите своё имя и фамилию:',
                    reply_markup=types.ReplyKeyboardRemove()
                )
                await Global.registration_name.set()
            else:
                user_data = await state.get_data()
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.add("Согласен", "Не согласен")
                await callback.message.answer(
                    f"Вы выбрали {user_data['chosen_bouquet']}. Для продолжения заказа требуется зарегистрироваться."
                    f"Даю согласия на обработку персональных данных?", reply_markup=keyboard)
                await Global.person_data.set()

        @dp.message_handler(state=Global.person_data)
        async def register_user(message: types.Message, state: FSMContext):
            if message.text == 'Согласен':
                await state.update_data(access='Access')
                await message.answer(
                    'Введите своё имя и фамилию:',
                    reply_markup=types.ReplyKeyboardRemove()
                )
                await Global.registration_name.set()
            else:
                await message.answer(
                    'Для продолжения необходимо дать разрешение на обработку персональных данных')
                await Global.person_data.set()

        # Регистрация

        @dp.message_handler(lambda message: message.text.count(' ') < 1 or message.text.count(' ') > 2,
                            state=Global.registration_name)
        async def get_valid_name(message: types.Message):
            await message.reply(
                'Введите правильное имя')

        @dp.message_handler(state=Global.registration_name)
        async def get_name(message: types.Message, state: FSMContext):
            await state.update_data(full_name=message.text)
            await message.answer(
                'Введите свой номер телефона:')

            await Global.registration_phonenumber.set()

        @dp.message_handler(state=Global.registration_phonenumber)
        async def get_phone_number(message: types.Message, state: FSMContext):
            if get_valid_phone(message.text):
                valid_number = get_valid_phone(message.text)
                await message.answer(f'Ваш номер: {valid_number}')
                await state.update_data(phone_number=valid_number)
                await message.answer(f'Теперь введем адрес, начнем с улицы:')
                await Global.address_street.set()
            else:
                await message.answer(f'Номер введен не верно, введите номер в формате \"+79876665544')
                await Global.registration_phonenumber.set()

        @dp.message_handler(state=Global.address_street)
        async def get_street(message: types.Message, state: FSMContext):
            await state.update_data(address_street=message.text)
            await message.answer(
                'Введите номер дома:')

            await Global.address_number_house.set()

        @dp.message_handler(state=Global.address_number_house)
        async def get_house_number(message: types.Message, state: FSMContext):
            await state.update_data(address_number_house=message.text)
            await message.answer(
                'Введите номер подъезда, если у вас частный дом поставьте 1:')

            await Global.address_number_driveway.set()

        @dp.message_handler(state=Global.address_number_driveway)
        async def get_house_driveway(message: types.Message, state: FSMContext):
            await state.update_data(address_number_driveway=message.text)
            await message.answer(
                'Введите номер квартиры:')

            await Global.address_number_flat.set()

        @dp.message_handler(state=Global.address_number_flat)
        async def get_order_info(message: types.Message, state: FSMContext):
            await state.update_data(address_number_flat=message.text)
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add("Главное меню")
            user_data = await state.get_data()

            user = User.objects.filter(chat_id=message['from'].id).update(access=True)
            courier = Courier.objects.get()
            user_id = User.objects.filter(chat_id=message['from'].id)

            user_address = f'{user_data["address_street"]}, {user_data["address_number_house"]}, {user_data["address_number_driveway"]}, {user_data["address_number_flat"]}'
            currentDateAndTime = datetime.now()
            print(currentDateAndTime)
            if user_data.get('bouquet_photo_id'):
                flower_id = user_data['bouquet_id']
                flower_obj = Flower.objects.get(pk=flower_id)
                created_order = Order.objects.create(user=user_id[0], flower=flower_obj, courier=courier,
                                                     address=user_address, delivery_date=currentDateAndTime)
                print(created_order)
                await message.answer(
                    '<b>Ваш заказ создан</b>')
                await bot.send_photo(chat_id=message.from_user.id, photo=user_data['bouquet_photo_id'],
                                     caption=f'<b>Букет: {user_data["chosen_bouquet"]}\n'
                                             f'Событие: {user_data["chosen_event"]}\n'
                                             f'Цена: {user_data["bouquet_price"]}\n'
                                             f'Адрес:\n'
                                             f'Улица: {user_data["address_street"]}\n'
                                             f'Номер дома: {user_data["address_number_house"]}\n'
                                             f'Номер подъезда: {user_data["address_number_driveway"]}\n'
                                             f'Номер квартиры: {user_data["address_number_flat"]}\n'
                                             f'Номер телефона: {user_data["phone_number"]}</b>')

                await state.finish()
                await asyncio.sleep(3)
                await flower_start(message)
            else:
                created_order = Order.objects.create(user=user_id[0], flower=None, courier=courier,
                                                     address=user_address, delivery_date=currentDateAndTime)

                await message.answer(
                    '<b>Ваш заказ создан, в ближайшее время с вами свяжется флорист.</b>')
                await bot.send_message(chat_id=message.from_user.id, text=
                f'<b>Букет: {user_data["chosen_bouquet"]}\n'
                f'Событие: {user_data["chosen_event"]}\n'
                f'Адрес:\n'
                f'Улица: {user_data["address_street"]}\n'
                f'Номер дома: {user_data["address_number_house"]}\n'
                f'Номер подъезда: {user_data["address_number_driveway"]}\n'
                f'Номер квартиры: {user_data["address_number_flat"]}\n'
                f'Номер телефона: {user_data["phone_number"]}</b>')

                await state.finish()
                await asyncio.sleep(3)
                await flower_start(message)

        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
