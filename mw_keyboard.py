from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.utils.callback_data import CallbackData

show_schedule = InlineKeyboardButton('Посмотреть расписание🙊🗓', callback_data='show_schedule')
show_homework = InlineKeyboardButton('Посмотреть домашнее задание 📖📚', callback_data='show_homework')
edit_schedule = InlineKeyboardButton('Редактировать расписание ✏️🗓', callback_data='edit_schedule')
edit_homework = InlineKeyboardButton('Редактировать домашнее задание ✏️📖', callback_data='edit_homework')
show_a_cat_kb = InlineKeyboardButton('Получить дозу мотивации 🐱🌷', callback_data='show_a_cat')
# add_to_someones_schedule = InlineKeyboardButton('Присоединиться к расписанию', callback_data='add_to_someones_schedule')
inlineKeyboardGreeting = InlineKeyboardMarkup(row_width=1).add(show_schedule,
                                                               show_homework,
                                                               edit_homework,
                                                               edit_schedule,
                                                               show_a_cat_kb)
"""Клавиатура-меню, чтобы `пользователь такой *тык* и его перекидывало на нужные штуки`"""

weekday_cd = CallbackData("w_w", "weekday")
monday = InlineKeyboardButton('Понедельник', callback_data=weekday_cd.new(weekday='monday'))
tuesday = InlineKeyboardButton('Вторник', callback_data=weekday_cd.new(weekday='tuesday'))
wednesday = InlineKeyboardButton('Среда', callback_data=weekday_cd.new(weekday='wednesday'))
thursday = InlineKeyboardButton('Четверг', callback_data=weekday_cd.new(weekday='thursday'))
friday = InlineKeyboardButton('Пятница', callback_data=weekday_cd.new(weekday='friday'))
saturday = InlineKeyboardButton('Суббота', callback_data=weekday_cd.new(weekday='saturday'))
sunday = InlineKeyboardButton('Воскресенье', callback_data=weekday_cd.new(weekday='sunday'))
week_schedule = [monday, tuesday, wednesday, thursday, friday, saturday, sunday]

inlineKeyboardWeekSchedule = InlineKeyboardMarkup().add(*week_schedule)
"""Клавиатура содержащая дни недели"""
