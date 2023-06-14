from __future__ import annotations

import io
from random import choice
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, InputFile

from motivation_caption import captions
from env import MV_TOKEN
from mw_keyboard import inlineKeyboardGreeting, inlineKeyboardWeekSchedule, weekday_cd

import logging
import requests

from enum import Enum

# Включает подробное логгирования для бота (в консоль)
logging.basicConfig(level=logging.INFO)


class Day(Enum):
    """Класс для дней недели"""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class BotStates(StatesGroup):
    """Хранит все возможные стейты пользователя в Finite State Machine"""
    edit_schedule_for_weekday = State()
    edit_homework_for_weekday = State()

    choose_weekday_to_edit_schedule = State()
    choose_weekday_to_show_schedule = State()

    choose_weekday_to_edit_homework = State()
    choose_weekday_to_show_homework = State()


class Homework:
    """Класс для домашнего задания (для отдельного пользователя), хранит все расписания по ключу (id пользователя)"""
    owner_id: int
    """Домашнее задание отдельного пользователя"""
    homework_by_days: dict[Day, str]
    """Нужно для хранение заданий пользователей"""
    __instances__: dict[int, Homework] = {}

    def __init__(self, owner_id: int):
        self.homework_by_days = dict()
        self.owner_id = owner_id

    @staticmethod
    def get_or_create_homework(owner_id: int):
        """Создаёт либо выдаёт уже существующий словарь заданий по ключу(id пользователя)

               :param owner_id: id пользователя
               :return: возвращает либо новый словарь заданий, либо тот, что уже существует
               """
        if owner_id not in Homework.__instances__:
            Homework.__instances__[owner_id] = Homework(owner_id)
        return Homework.__instances__[owner_id]

    @staticmethod
    def get(owner_id: int):
        """Выдаёт уже существующие задания по ключу(id пользователя), либо возвращает None

                :param owner_id: id пользователя
                :return: возвращает существующие задания либо None
                """
        return Homework.__instances__.get(owner_id)

    def get_for_day(self, day: Day | str):
        """Возвращает расписание на день

                :param day: день недели
                :return: строка, содержащая задания
                """
        day = Day(day)
        return self.homework_by_days.get(day)

    def set_for_day(self, day: Day | str, assignments: str):
        """Добавляет задания пользователя на день

               :param day: день недели
               :param subjects: строка заданий
               """
        day = Day(day)
        self.homework_by_days[day] = assignments

    def __str__(self):
        return str(self.homework_by_days)


class Schedule:
    """Класс для расписания (для отдельного пользователя), хранит все расписания по ключу (id пользователя)"""
    owner_id: int
    schedule_by_days: dict[Day, str]
    """Расписание отдельного пользователя"""
    __instances__: dict[int, Schedule] = {}
    """Нужно для хранение расписаний пользователей"""

    def __init__(self, owner_id: int):
        self.schedule_by_days = dict()
        self.owner_id = owner_id

    @staticmethod
    def get_or_create_schedule(owner_id: int) -> Schedule:  # Singleton or FlyWeight
        """Создаёт либо выдаёт уже существующее расписание по ключу(id пользователя)

        :param owner_id: id пользователя
        :return: возвращает либо новое расписание, либо то, что уже существует
        """
        if owner_id not in Schedule.__instances__:
            Schedule.__instances__[owner_id] = Schedule(owner_id)
        return Schedule.__instances__[owner_id]

    @staticmethod
    def get(owner_id: int) -> Schedule | None:
        """Выдаёт уже существующее расписание по ключу(id пользователя), либо возвращает None

        :param owner_id: id пользователя
        :return: возвращает существующее расписание либо None
        """
        return Schedule.__instances__.get(owner_id)

    def get_for_day(self, day: Day | str):
        """Возвращает расписание на день

        :param day: день недели
        :return: строка, содержащая предметы
        """
        day = Day(day)
        return self.schedule_by_days.get(day)

    def set_for_day(self, day: Day | str, subjects: str):
        """Добавляет предметы в расписание пользователя на день

        :param day: день недели
        :param subjects: список/строка предметов
        """
        day = Day(day)
        self.schedule_by_days[day] = subjects

    def __str__(self):
        return str(self.schedule_by_days)


# Инициализировать бота и задать диспетчера
bot = Bot(token=MV_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


@dp.message_handler(commands=['start'], state="*")
async def start(message: Message, state: FSMContext):
    """Обработчик для запуска бота:
    1) Получаем расписание и список дз пользователя если оно есть, иначе — создаём.
    2) Отправляем привественное сообщение пользователю с клавиатурой
    :param message: сообщение от пользователя
    :param state: state пользователя
    """
    schedule = Schedule.get_or_create_schedule(message.from_id)
    homework = Homework.get_or_create_homework(message.from_id)
    await message.answer(
        f'Привет, {message.from_user.username}! Добро пожаловать в Motivation and Study Bot!'
        '\nЗдесь ты можешь устанвливать свое расписание'
        '\nи добавлять свои домашние задния'
        '\n(а еще получить мотивирующую милую картинку ;).'
        '\nИспользуй кнопки ниже, чтобы выбрать режим.'
        '\nСохраняй мотивацию и выполняй задания <3', reply_markup=inlineKeyboardGreeting)


@dp.callback_query_handler(text='show_schedule', state="*")
async def show_schedule(call: types.CallbackQuery, state: FSMContext):
    """callback для кнопки "посмотреть расписание":
     1) Выводится лист кнопок - список дней недели
     2) Устанавливается state для выбора дня недели для демонстрации расписания
     :param call: callback inline кнопки
     :param state: state пользователя"""
    await bot.send_message(call.from_user.id, 'Выбери день: ', reply_markup=inlineKeyboardWeekSchedule)
    await BotStates.choose_weekday_to_show_schedule.set()


#
@dp.callback_query_handler(weekday_cd.filter(), state=BotStates.choose_weekday_to_show_schedule)
async def _(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """callback для кнопки дней недели (для демонстрации расписания)
    1) Получаем значение weekday - день недели, кнопка которго была активирована
    2) Получаем расписание пользователя (оно точно существует см. start)
    3) Из расписания пользователя получаем расписание на день
    4) Проверяем не пустое ли расписание на день.
    Если пустое - просим пользователя добавить расписание, иначе выводим расписание на день
    :param call: callback inline кнопки
    :param callback_data: значение кнопки, полученное из weekday_cd.filter()
    :param state: state пользователя"""
    weekday = callback_data.get("weekday")
    schedule: Schedule = Schedule.get(call.from_user.id)
    day_schedule = schedule.get_for_day(weekday)
    if day_schedule is None:
        await call.message.answer(f"Сначала добавь своё расписание на этот день")
    else:
        text = f"Вот твое расписание на день:\n{day_schedule}"
        await call.message.answer(text)


@dp.callback_query_handler(text='show_homework', state='*')
async def show_homework(call: types.CallbackQuery, state: FSMContext):
    """callback для кнопки "посмотреть дз" - выводится лист кнопок - список дней недели
    1) Выводится лист кнопок - список дней недели
    2) Устанавливается state для выбора дня недели для демонстрации расписания
    :param call: callback inline кнопки
    :param state: state пользователя"""
    await bot.send_message(call.from_user.id, 'Выбери день: ', reply_markup=inlineKeyboardWeekSchedule)

    await BotStates.choose_weekday_to_show_homework.set()


@dp.callback_query_handler(weekday_cd.filter(), state=BotStates.choose_weekday_to_show_homework)
async def _(call: types.CallbackQuery, callback_data: dict):
    """callback для кнопки дней недели (демонстрация домашнего задания)
    1) Получаем значение weekday - день недели, кнопка которго была активирована
    2) Получаем задания пользователя (они точно существует см. start)
    3) Из заданий пользователя получаем задания на день
    4) Проверяем есть ли задания на день.
    Если нет - просим пользователя добавить задания, иначе выводим задания на день
    :param call: callback inline кнопки
    :param callback_data: значение кнопки, полученное из weekday_cd.filter() """
    weekday = callback_data.get("weekday")
    homework: Homework = Homework.get(call.from_user.id)
    day_homework = homework.get_for_day(weekday)
    if day_homework is None:
        await call.message.answer("Сначала добавь домашнее задание!")
    else:
        text = f"Вот твои задания на день:\n{day_homework}"
        await call.message.answer(text)


@dp.callback_query_handler(text='edit_homework', state="*")
async def edit_homework(call: types.CallbackQuery, state: FSMContext):
    """callback для кнопки "редактировать домашнее задание"
     1) Просим пользователя выбрать день, для которого нужно изменить задания,
        и выводим клавиатуру - список дней недели
    2) Устанавливается state для выбора дня, для которого нужно изменить задания
    :param call: callback inline кнопки
    :param state: state пользователя"""
    await bot.send_message(call.from_user.id, 'Выбери день, для которго хочешь изменить домашнее задание: ',
                           reply_markup=inlineKeyboardWeekSchedule)
    await BotStates.choose_weekday_to_edit_homework.set()


# callback для кнопки дней недели (изменение домашнего задания)
@dp.callback_query_handler(weekday_cd.filter(), state=BotStates.choose_weekday_to_edit_homework)
async def _(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """callback для кнопки дней недели (изменение домашнего задания)
        1) Получаем weekday - день недели, кнопка которого была активирована.
        2) Запоминаем значение weekday
        3) Установаливаем state для редактирования заданий на определенного дня недели
        4) Просим пользователя ввести список предметов и заданий к ним
        :param call: callback inline кнопки
        :param callback_data: значение кнопки, полученное из weekday_cd.filter()
        :param state: state пользователя"""
    weekday = callback_data.get("weekday")
    await state.update_data(chosen_weekday=weekday)
    await BotStates.edit_homework_for_weekday.set()
    await call.message.answer(
        'Введи свои задания списком. Вот так:\nclass 1: assignments 1\nclass 2: assignments 2\n... ')


@dp.callback_query_handler(text='edit_schedule', state="*")
async def edit_schedule(call: types.CallbackQuery, state: FSMContext):
    """callback для кнопки "редактировать расписание"
        1) Просим пользователя выбрать день, для которого нужно изменить расписание,
        и выводим клавиатуру - список дней недели
        2) Устанавливается state для выбора дня, для которого нужно изменить расписание
        :param call: callback inline кнопки
        :param state: state пользователя"""
    # await bot.answer_callback_query(callback_query.id, 'Callback Answered!')  # это всплывающее окно
    await bot.send_message(call.from_user.id, 'Выбери день, который хочешь изменить: ',
                           reply_markup=inlineKeyboardWeekSchedule)
    await BotStates.choose_weekday_to_edit_schedule.set()


@dp.callback_query_handler(weekday_cd.filter(), state=BotStates.choose_weekday_to_edit_schedule)
async def _(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """callback для кнопки дней недели (изменение расписания)
    1) Получаем weekday - день недели, кнопка которого была активирована.
    2) Запоминаем значение weekday
    3) Установаливаем state для редактирования расписания определенного дня недели
    4) Просим пользователя ввести список предметов
    :param call: callback inline кнопки
    :param callback_data: значение кнопки, полученное из weekday_cd.filter()
    :param state: state пользователя"""
    weekday = callback_data.get("weekday")
    await state.update_data(chosen_weekday=weekday)
    await BotStates.edit_schedule_for_weekday.set()
    await call.message.answer('Введи свои предметы списком. Вот так:\nclass 1\nclass 2\nclass 3\n... ')


@dp.message_handler(state=BotStates.edit_schedule_for_weekday)
async def _(message: Message, state: FSMContext):
    """Метод, который получает сообщение от пользователя и запоминает его список придметов в словарь schedule.day_schedule
    по ключу [weekday]
    1) Получаем значение weekday из state
    2) Получаем расписание пользователя через его id
    3) Из сообщения пользователя получаем список предметов, которые затем добавляем в его расписание
    4) Отправляем расписание на день пользователю
    :param message: сообщение пользователя
    :param state: state пользователя"""
    data = await state.get_data()
    weekday = data['chosen_weekday']

    schedule = Schedule.get(message.from_id)

    subjects = message.text
    schedule.set_for_day(weekday, subjects)

    await message.answer(f'Твоё расписание:\n{schedule.get_for_day(weekday)}')


@dp.message_handler(state=BotStates.edit_homework_for_weekday)
async def _(message: Message, state: FSMContext):
    """Метод, который получает сообщение от пользователя и запоминает его список задний в словарь
    homework.homework_for_days по ключу [weekday]
    1) Получаем значение weekday из state
    2) Получаем список заданий пользователя через его id
    3) Из сообщения пользователя получаем список предметов и заданий к ним, которые затем добавляем в его задания
    4) Отправляем задания на день пользователю
    :param message: сообщение пользователя
    :param state: state пользователя"""
    data = await state.get_data()
    weekday = data['chosen_weekday']

    homework = Homework.get(message.from_id)

    assignments = message.text
    homework.set_for_day(weekday, assignments)

    await message.answer(f'Твои задания:\n{homework.get_for_day(weekday)}')


# вот эта часть работает охуенно ее не трогать
# callback для котиков
@dp.callback_query_handler(text='show_a_cat', state="*")
async def show_a_cat(call: types.CallbackQuery):
    """Метод, который обрабатывает callback кнопки "Получить дозу мотивации"
        1) Получает img (картинку) из метода get_cat()
        2) Случайно выбирает одну из фраз из элементов списка captions
        3) Проверяет, не является ли пустой img.
    Если нет, то отправляет ее пользователю и выводит клавиатуру главного меню
    :param call: callback inline кнопки"""
    img = get_cat()
    caption = choice(captions)
    if img:
        await bot.send_photo(call.from_user.id, img, caption=caption, reply_markup=inlineKeyboardGreeting)


def get_cat() -> InputFile:
    """Метод, который возращает картинку, полученную по API
    1) с помощью библиотеки requests получаем url
    2) Записываем картинку в буффер в байтах
    :return: img - картинка котика"""
    link = 'https://api.thecatapi.com/v1/images/search'
    answer: list[dict: str | int] = requests.get(link).json()
    url_s = []
    for i in answer:
        url_s.append(i.get('url'))

    for url in url_s:
        data = requests.get(url).content
        buf = io.BytesIO(data)
        # buf.seek(0)
        img = InputFile(buf)
        return img


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
