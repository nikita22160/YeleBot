import datetime
import re

import telebot
import gspread
import gspread_formatting as gspf

"""
Перед тем, как использовать данный скрипт, нужно создать бота через @BotFather
в Telegram и вставить его токен в файл token.txt

Далее нужно подготовить аккаунт Google. Следуйте уроку на сайте
https://habr.com/ru/articles/483302/
Читайте от заголовка "Регистрация в сервисах Google и установка библиотек" до "Теперь переходим к установке библиотек."
Скачанный .json файл с ключом добавьте в папку с данным скриптом и переименуйте его в "service_account.json"

Далее скрипт должен запуститься.
Также вы можете установить список команд в BotFather:
1. Отправьте /setcommands
2. Выберете нужного бота
3. Отправьте следующее:
start - Список команд
cancel - Отмена действия
create - Создать Google таблицу с заметками
addnote - Добавить заметку в Google таблицу
findnote - Найти заметку, изменить или удалить найденную заметку
deleteall - Удалить все заметки в таблице

"""

with open("token.txt") as file:
    token = file.read()
bot = telebot.TeleBot(token)
gc = gspread.service_account("service_account.json")
event_data = {}


def check_cancel(message):
    if message.text == "/cancel" or '/' in message.text or \
            message.text == "❌ Отмена":
        bot.send_message(message.from_user.id, "Отмена действия.")
        return True
    return False


def get_table(message):
    try:
        result = gc.open_by_key(message.text)
    except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound):
        try:
            result = gc.open(message.text)
        except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound):
            bot.send_message(message.from_user.id, "Таблица не найдена.")
            return False
    event_data["table"] = result
    return True


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text == "/start":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = telebot.types.KeyboardButton("💡 Создать таблицу")
        btn2 = telebot.types.KeyboardButton("📝 Добавить заметку")
        btn3 = telebot.types.KeyboardButton("🔍 Найти заметку и совершить действия")
        btn4 = telebot.types.KeyboardButton("❌ Отмена")
        btn5 = telebot.types.KeyboardButton("🗑 Удалить все заметки")
        markup.add(btn1, btn2, btn3, btn4, btn5)

        bot.send_message(message.from_user.id,
                         "Привет.\n"
                         "Чтобы создать таблицу с заметками, введите /create\n"
                         "Чтобы отменить команду в любой момент, введите /cancel\n"
                         "Чтобы добавить заметку, введите /addnote\n"
                         "Чтобы найти заметки и произвести действия, введите /findnote\n"
                         "Чтобы удалить все заметки, введите /deleteall",
                         reply_markup=markup)
    elif message.text == "/create" or message.text == "💡 Создать таблицу":
        bot.send_message(message.from_user.id, "Назовите файл с заметками.")
        bot.register_next_step_handler(message, create_get_name)
    elif message.text == "/addnote" or message.text == "📝 Добавить заметку":
        bot.send_message(message.from_user.id, "Введите ID таблицы либо её название файла с заметками.")
        bot.register_next_step_handler(message, addnote_tableid)
    elif message.text == "/findnote" or message.text == "🔍 Найти заметку и совершить действия":
        bot.send_message(message.from_user.id, "Введите ID таблицы либо её название файла с заметками.")
        bot.register_next_step_handler(message, findnote_tableid)
    elif message.text == "/deleteall" or message.text == "🗑 Удалить все заметки":
        bot.send_message(message.from_user.id, "Введите ID таблицы либо её название файла с заметками.")
        bot.register_next_step_handler(message, deleteall)
    else:
        bot.send_message(message.from_user.id, "Нераспознанная команда.")


# Создание файла с заметками

def create_get_name(message):
    if check_cancel(message): return

    event_data["name"] = message.text
    bot.send_message(message.from_user.id, "Назовите свой адрес электронной почты, "
                                           "чтобы бот мог выдать доступ к файлу.")
    bot.register_next_step_handler(message, create_get_email)


def create_get_email(message):
    if check_cancel(message): return

    if '@' not in message.text:
        bot.send_message(message.from_user.id, "Вы ввели неправильный адрес электронной почты. Попробуйте снова.")
        bot.register_next_step_handler(message, create_get_email)
        return

    event_data["email"] = message.text
    bot.send_message(message.from_user.id, "(По желанию) Введите своё имя/псевдоним,"
                                           "чтобы отображать его в заголовке таблицы,"
                                           "или напишите \"Нет\".")
    bot.register_next_step_handler(message, create_get_person_name)


def create_get_person_name(message):
    if check_cancel(message): return

    if message.text.lower() != "нет":
        event_data["person_name"] = message.text
    else:
        event_data["person_name"] = ""
    create_create_sheet(message)


def create_create_sheet(message):
    if check_cancel(message): return

    bot.send_message(message.from_user.id, f"Создаю Google таблицу \"{event_data['name']}\"...")
    sheet = gc.create(event_data["name"])
    sheet.share(event_data["email"], perm_type="user", role="writer")
    worksheet = sheet.sheet1

    if event_data["person_name"]:
        worksheet.update("A1", f"Список заметок \"{event_data['person_name']}\"")
    else:
        worksheet.update("A1", f"Список заметок")

    worksheet.update("A2", [["Задание", "Начальная дата", "Конечная дата", "Степень важности", "Статус"]])
    gspf.set_column_width(worksheet, 'A', 200)
    gspf.set_column_width(worksheet, 'B', 150)
    gspf.set_column_width(worksheet, 'C', 150)
    gspf.set_column_width(worksheet, 'D', 150)
    gspf.set_column_width(worksheet, 'F', 100)
    gspf.format_cell_range(worksheet, "A2:F2",
                           gspf.CellFormat(textFormat=gspf.TextFormat(bold=True)))

    link = "https://docs.google.com/spreadsheets/d/" + sheet.id
    bot.send_message(message.from_user.id, f"Ссылка на Google таблицу: {link}\n"
                                           f"ID таблицы: {sheet.id}\n"
                                           "Не теряйте ID таблицы, так как (если вы забудете имя таблицы) "
                                           "изменения можно провести только через него.\n"
                                           "Чтобы добавить заметку, используйте команду /addnote\n"
                                           "Чтобы совершить поиск по заметкам и выполнить действия над ними, "
                                           "используйте команду /findnote")


# Создание заметки

def addnote_tableid(message):
    if check_cancel(message): return

    if get_table(message):
        bot.send_message(message.from_user.id, "Введите следующие данные, используя новую строку как разделитель:\n"
                                               "Задание, начальная дата, конечная дата, степень важности, статус.\n"
                                               "\"Задание\" и \"Степень важности\" могут быть любым текстом.\n"
                                               "Формат для дат следующий: ДД-ММ-ГГГГ. Вставьте \"!\", чтобы "
                                               "использовать сегодняшнюю дату. Вставьте \"-\", чтобы оставить поле"
                                               "пустым.\n"
                                               "Статус также может быть любым текстом, но рекомендуется использовать "
                                               "\"В процессе\", \"Закончено\" или \"Отложено\".\n"
                                               "Поле статуса и степени важности могут быть заменены прочерком (\"-\")"
                                               " или пропущены. В таком случае будут введены значения по умолчанию "
                                               "(\"В процессе\" и \"Опционально\" соответственно).")
        bot.register_next_step_handler(message, addnote_data)


def addnote_data(message):
    if check_cancel(message): return

    data = message.text.split('\n')
    if len(data) < 3:
        bot.send_message(message.from_user.id, "Неправильный формат ответа (количество строк меньше, чем 3).")
        return

    if data[0].strip() == "":
        bot.send_message(message.from_user.id, "Текст задания не может быть пустым.")
        return

    try:
        if data[1] == "!":
            data[1] = datetime.date.today().strftime('%d-%m-%Y')
        elif data[1] == "-":
            data[1] = ""
        else:
            date = [int(i) for i in data[1].split('-')]
            data[1] = datetime.date(date[2], date[1], date[0]).strftime('%d-%m-%Y')

        if data[2] == "!":
            data[2] = datetime.date.today().strftime('%d-%m-%Y')
        elif data[2] == "-":
            data[2] = ""
        else:
            date = [int(i) for i in data[2].split('-')]
            data[2] = datetime.date(date[2], date[1], date[0]).strftime('%d-%m-%Y')
    except ValueError:
        bot.send_message(message.from_user.id, "Дата введена в неправильном формате. Убедитесь, "
                                               "что она была введена в формате ДД-ММ-ГГГГ.")
        return

    bot.send_message(message.from_user.id, "Добавляю заметку в таблицу...")

    if len(data) == 3:
        data.extend(["Опционально", "В процессе"])
    elif len(data) == 4:
        data.extend(["В процессе"])
    else:
        if data[3].strip() == "":
            data[3] = "Опционально"
        if data[4].strip() == "":
            data[4] = "В процессе"

    sheet = event_data["table"]
    worksheet = sheet.sheet1
    row = 3
    while worksheet.cell(row, 1).value:
        row += 1
    worksheet.update(f"A{row}", [data])

    bot.send_message(message.from_user.id, f"Заметка успешно добавлена в строку под номером {row}!")


# Поиск заметки

def findnote_tableid(message):
    if check_cancel(message): return

    if get_table(message):
        bot.send_message(message.from_user.id, "Введите номер строки с заметкой или данные заметки.\n"
                                               "Обратите внимание, что поиск зависит от регистра!")
        bot.register_next_step_handler(message, findnote_data)


def findnote_data(message):
    if check_cancel(message): return

    if message.text.isnumeric():
        sheet = event_data["table"]
        worksheet = sheet.sheet1

        row = int(message.text)
        if not worksheet.cell(row, 1):
            bot.send_message(message.from_user.id, "Данная строка пуста.")
            return
        if row < 3:
            bot.send_message(message.from_user.id, "Данный номер строки выходит за пределы таблицы заметок.")
            return

        markup = telebot.types.InlineKeyboardMarkup()
        btn_edit = telebot.types.InlineKeyboardButton(text="Изменить", callback_data="EditNote")
        btn_delete = telebot.types.InlineKeyboardButton(text="Удалить", callback_data="DeleteNote")
        markup.add(btn_edit)
        markup.add(btn_delete)

        row_str = '\n'.join(worksheet.row_values(row))
        bot.send_message(message.from_user.id, f"Заметка №{row}: {row_str}",
                         reply_markup=markup)
        return

    bot.send_message(message.from_user.id, "Ищу заметку...")

    sheet = event_data["table"]
    worksheet = sheet.sheet1
    regular_expr = re.compile(message.text, re.I)
    cell_list = worksheet.findall(regular_expr)

    if len(cell_list) > 0:
        for cell in cell_list:
            markup = telebot.types.InlineKeyboardMarkup()
            btn_edit = telebot.types.InlineKeyboardButton(text="Изменить", callback_data="EditNote")
            btn_delete = telebot.types.InlineKeyboardButton(text="Удалить", callback_data="DeleteNote")
            markup.add(btn_edit)
            markup.add(btn_delete)

            row = cell.row
            row_str = '\n'.join(worksheet.row_values(row))
            bot.send_message(message.from_user.id, f"Заметка №{row}: {row_str}",
                             reply_markup=markup)
    else:
        bot.send_message(message.from_user.id, "Заметки не найдены. Попробуйте поменять критерии поиска.")


def deleteall(message):
    if check_cancel(message): return

    if get_table(message):
        markup = telebot.types.InlineKeyboardMarkup()
        btn_yes = telebot.types.InlineKeyboardButton(text="Да", callback_data="DeleteAll")
        markup.add(btn_yes)
        bot.send_message(message.from_user.id, "Вы уверены в том, что хотите удалить все заметки в таблице \""
                                               f"{event_data['table'].title}\"? "
                                               "Восстановить их будет невозможно!",
                         reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "EditNote":
        text = call.message.text
        start = text.find('№')
        end = text.find(':')
        row = int(text[start + 1:end])

        event_data["row"] = row
        bot.send_message(call.message.chat.id, "Введите новые данные для ячейки.\n"
                                               "Введите следующие данные, используя новую строку как разделитель:\n"
                                               "Задание, начальная дата, конечная дата, степень важности, статус.\n"
                                               "\"Задание\" и \"Степень важности\" могут быть любым текстом.\n"
                                               "Формат для дат следующий: ДД-ММ-ГГГГ. Вставьте \"!\", чтобы "
                                               "использовать сегодняшнюю дату. Вставьте \"-\", чтобы оставить поле"
                                               "пустым.\n"
                                               "Статус также может быть любым текстом, но рекомендуется использовать "
                                               "\"В процессе\", \"Закончено\" или \"Отложено\".\n"
                                               "Поле статуса и степени важности могут быть пропущены. "
                                               "В таком случае будут введены значения по умолчанию "
                                               "(\"В процессе\" и \"Опционально\" соответственно).")
        bot.register_next_step_handler(call.message, editnote)
    elif call.data == "DeleteNote":
        text = call.message.text
        start = text.find('№')
        end = text.find(':')
        row = int(text[start + 1:end])

        bot.send_message(call.message.chat.id, "Удаляю заметку из таблицы...")
        sheet = event_data["table"]
        worksheet = sheet.sheet1
        worksheet.copy_range(f"A{row + 1}:E{worksheet.row_count}", f"A{row}")
        worksheet.update(f"A{worksheet.row_count}", [[""] * 5])
        bot.send_message(call.message.chat.id, "Заметка успешно удалена!")
    elif call.data == "DeleteAll":
        sheet = event_data["table"]
        worksheet = sheet.sheet1
        worksheet.update("A3", [[""] * 5] * (worksheet.row_count - 3))
        bot.send_message(call.message.chat.id, "Заметки успешно удалены.")
    else:
        print("a", call.data)


def editnote(message):
    if check_cancel(message): return

    data = message.text.split('\n')
    if len(data) < 3:
        bot.send_message(message.from_user.id, "Неправильный формат ответа (количество строк меньше, чем 3).")
        return

    try:
        if data[1] == "!":
            data[1] = datetime.date.today().strftime('%d-%m-%Y')
        elif data[1] == "-":
            data[1] = ""
        else:
            date = [int(i) for i in data[1].split('-')]
            data[1] = datetime.date(date[2], date[1], date[0]).strftime('%d-%m-%Y')

        if data[2] == "!":
            data[2] = datetime.date.today().strftime('%d-%m-%Y')
        elif data[2] == "-":
            data[2] = ""
        else:
            date = [int(i) for i in data[2].split('-')]
            data[2] = datetime.date(date[2], date[1], date[0]).strftime('%d-%m-%Y')
    except ValueError:
        bot.send_message(message.from_user.id, "Дата введена в неправильном формате. Убедитесь, "
                                               "что она была введена в формате ДД-ММ-ГГГГ.")
        return

    if len(data) == 3:
        data.extend(["Опционально", "В процессе"])
    elif len(data) == 4:
        data.extend(["В процессе"])
    else:
        if data[3].strip() == "":
            data[3] = "Опционально"
        if data[4].strip() == "":
            data[4] = "В процессе"

    bot.send_message(message.from_user.id, "Изменяю заметку в таблице...")

    sheet = event_data["table"]
    worksheet = sheet.sheet1
    worksheet.update(f"A{event_data['row']}", [data])

    bot.send_message(message.from_user.id, "Заметка успешно изменена!")


bot.polling(none_stop=True, interval=0)
