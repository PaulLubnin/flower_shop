import os
from itertools import cycle

import phonenumbers
from aiogram import Bot, Dispatcher
from aiogram import executor
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from django.core.management import BaseCommand
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

events = ['день рождения', 'свадьба', 'восьмое марта', 'рождение ребенка', 'свой вариант/консультация']

budgets = {
    'До 1000р': range(1000),
    'До 5000р': range(5000),
    'До 10000р': range(10000),
    'Более 10000р': range(10001, 300000)
}
catalog = {
    'compositions': {
        'filepath': "3137.jpg",
        'caption': 'Этот букет несет в себе всю нежность ваших чувств и не способен оставить равнодушных '
                   'ни одного сердца!',
        'price': 500,
        'event': 'свадьба'
    },
    'compositions1': {
        'filepath': "586e0d6adfade_30.jpg",
        'caption': 'Этот букет несет в себе еще что-то',
        'price': 6000,
        'event': 'рождение ребенка'
    },
    'compositions2': {
        'filepath': "13---_enl.jpg",
        'caption': 'Этот букет несет счастье',
        'price': 1500,
        'event': 'день рождения'
    },
    'compositions3': {
        'filepath': "img-2122032.jpg",
        'caption': 'Этот букет несет в себе растраты',
        'price': 11900,
        'event': 'восьмое марта'
    },
}


def get_valid_phone(input_number: str):
    try:
        parse_number = phonenumbers.parse(input_number, "RU")
        national_number = phonenumbers.format_number(parse_number, phonenumbers.PhoneNumberFormat.E164)
        if phonenumbers.is_valid_number(parse_number):
            return national_number
    except phonenumbers.NumberParseException:
        print("Номер введен не верно, введите номер в формате \"+79876665544")


class Global(StatesGroup):
    event = State()
    our_event = State()
    budget = State()
    bouquet = State()
    person_data = State()
    registration_name = State()
    registration_phonenumber = State()
    cancel = State()
    our_budget = State()
    address_street = State()
    address_number_house = State()
    address_number_flat = State()
    address_number_driveway = State()


class Command(BaseCommand):
    help = 'Запуск чат-бота'

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

        cycle_pfilepath = cycle(catalog.items())

        @dp.message_handler(lambda message: message.text == "Главное меню", state="*")
        @dp.message_handler(commands="start", state="*")
        async def flower_start(message: types.Message):
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for event in events:
                keyboard.insert(event)
            await message.answer(
                "<b>Добро пожаловать! Вас приветствует бот для заказа букетов\n"
                "К какому событию готовимся? Выберите один из вариантов, либо укажите свой</b>",
                reply_markup=keyboard
            )
            await Global.event.set()

        # Ветка свой вариант
        @dp.message_handler(lambda message: message.text == "свой вариант/консультация", state=Global.event)
        async def get_event(message: types.Message, state: FSMContext):
            await state.update_data(chosen_event=message.text)
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for description, budget in budgets.items():
                keyboard.insert(description)
            await message.answer(
                "<b>Укажите событие для которого требуется букет?</b>",
                reply_markup=ReplyKeyboardRemove()
            )
            await Global.our_event.set()

        @dp.message_handler(state=Global.our_event)
        async def get_our_budget(message: types.Message, state: FSMContext):
            await state.update_data(chosen_event=message.text)
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for description, budget in budgets.items():
                keyboard.insert(description)
            await message.answer("<b>Укажите бюджет</b>")
            await Global.our_budget.set()

        @dp.message_handler(state=Global.our_budget)
        async def get_our_access(message: types.Message, state: FSMContext):
            await state.update_data(chosen_price=message.text)
            await state.update_data(chosen_bouquet='консультация')
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add("Согласен", "Не согласен")
            await message.answer(
                "<b>Ваша заявка будет передана флористу, для обсуждения деталей вам требуется "
                "зарегистрироваться. "
                "Даю согласия на обработку персональных данных?</b>",
                reply_markup=keyboard
            )
            await Global.person_data.set()

        # Ветка с выбором изм меню
        @dp.message_handler(state=Global.event)
        async def get_event(message: types.Message, state: FSMContext):
            await state.update_data(chosen_event=message.text)
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for description, budget in budgets.items():
                keyboard.insert(description)
            await message.answer(
                "<b>На какой бюджет расчитываем?</b>",
                reply_markup=keyboard
            )
            await Global.budget.set()

        @dp.message_handler(state=Global.budget)
        async def get_budget(message: types.Message, state: FSMContext):
            await state.update_data(chosen_price=budgets[message.text])
            await message.answer("<b>Теперь выберем букет</b>")

            # for budget in get_budgets_filtered(evnet=user_data['chosen_event'], #Требуется функция фильтрации букета по двум параметрам
            #                                    price=user_data['chosen_price']):
            #     keyboard.insert(budget)

            next_bouquet = next(cycle_pfilepath)
            order_button = InlineKeyboardButton(f'Заказать {next_bouquet[0]}', callback_data=f'{next_bouquet[0]}')
            next_btn = InlineKeyboardButton(text="next", callback_data="Следующий букет")
            ikb = InlineKeyboardMarkup().add(order_button, next_btn)
            await bot.send_photo(
                message.from_user.id,
                photo=open(f'img/{dict(next_bouquet[1])["filepath"]}', 'rb'),
                caption=f'{dict(next_bouquet[1])["caption"]},'
                        f' цена: {dict(next_bouquet[1])["price"]}',
                reply_markup=ikb
            )
            await Global.bouquet.set()

        @dp.callback_query_handler(text="Следующий букет", state=Global.bouquet)
        async def get_next(message: types.Message):
            next_bouquet = next(cycle_pfilepath)
            order_button = InlineKeyboardButton(f'Заказать {next_bouquet[0]}', callback_data=f'{next_bouquet[0]}')
            next_btn = InlineKeyboardButton(text="next", callback_data="Следующий букет")
            ikb = InlineKeyboardMarkup().add(order_button, next_btn)
            await bot.send_photo(
                message.from_user.id,
                photo=open(f'img/{dict(next_bouquet[1])["filepath"]}', 'rb'),
                caption=f'{dict(next_bouquet[1])["caption"]},'
                        f' цена: {dict(next_bouquet[1])["price"]}',
                reply_markup=ikb
            )
            await Global.bouquet.set()

        @dp.callback_query_handler(lambda callback_query: callback_query, state=Global.bouquet)
        async def get_access(callback: types.CallbackQuery, state: FSMContext) -> None:
            await state.update_data(chosen_bouquet=callback.data)
            await state.update_data(bouquet_photo_id=callback.message["photo"][0]["file_id"])
            await state.update_data(bouquet_price=catalog[f'{callback.data}']['price'])
            user_data = await state.get_data()
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add("Согласен", "Не согласен")
            await callback.message.answer(
                f"Вы выбрали {user_data['chosen_bouquet']}. Для продолжения заказа требуется зарегистрироваться."
                f"Даю согласия на обработку персональных данных?",
                reply_markup=keyboard
            )
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
                await message.answer('Для продолжения необходимо дать разрешение на обработку персональных данных')
                await Global.person_data.set()

        # Регистрация
        @dp.message_handler(lambda message: message.text.isdigit(), state=Global.registration_name)
        async def get_valid_name(message: types.Message):
            await message.reply('Введите правильное имя')

        @dp.message_handler(state=Global.registration_name)
        async def get_name(message: types.Message, state: FSMContext):
            await state.update_data(full_name=message.text)
            await message.answer('Введите свой номер телефона:')

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
            await message.answer('Введите номер дома:')
            await Global.address_number_house.set()

        @dp.message_handler(state=Global.address_number_house)
        async def get_house_number(message: types.Message, state: FSMContext):
            await state.update_data(address_number_house=message.text)
            await message.answer('Введите номер подъезда, если у вас частный дом поставьте 1:')
            await Global.address_number_driveway.set()

        @dp.message_handler(state=Global.address_number_driveway)
        async def get_house_driveway(message: types.Message, state: FSMContext):
            await state.update_data(address_number_driveway=message.text)
            await message.answer('Введите номер квартиры:')
            await Global.address_number_flat.set()

        @dp.message_handler(state=Global.address_number_flat)
        async def get_order_info(message: types.Message, state: FSMContext):
            await state.update_data(address_number_flat=message.text)
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add("Главное меню")
            user_data = await state.get_data()
            if user_data.get('bouquet_photo_id'):
                await message.reply('Ваш заказ создан')
                await bot.send_photo(
                    chat_id=message.from_user.id,
                    photo=user_data['bouquet_photo_id'],
                    caption=f'<b>Букет: {user_data["chosen_bouquet"]}\n'
                            f'Событие: {user_data["chosen_event"]}\n'
                            f'Цена: {user_data["bouquet_price"]}\n'
                            f'Адрес:\n'
                            f'Улица: {user_data["address_street"]}\n'
                            f'Номер дома: {user_data["address_number_house"]}\n'
                            f'Номер подъезда: {user_data["address_number_driveway"]}\n'
                            f'Номер квартиры: {user_data["address_number_flat"]}\n'
                            f'Номер телефона: {user_data["phone_number"]}</b>',
                    reply_markup=keyboard)

                await state.finish()
            else:
                await message.reply(
                    'Ваш заказ создан, в ближайшее время с вами свяжется флорист.'
                )
                await bot.send_message(
                    chat_id=message.from_user.id, text=
                    f'<b>Букет: {user_data["chosen_bouquet"]}\n'
                    f'Событие: {user_data["chosen_event"]}\n'
                    f'Адрес:\n'
                    f'Улица: {user_data["address_street"]}\n'
                    f'Номер дома: {user_data["address_number_house"]}\n'
                    f'Номер подъезда: {user_data["address_number_driveway"]}\n'
                    f'Номер квартиры: {user_data["address_number_flat"]}\n'
                    f'Номер телефона: {user_data["phone_number"]}</b>', reply_markup=keyboard
                )

                await state.finish()

        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)