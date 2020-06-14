from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
import logging
import config
import get_rzd_info

logging.basicConfig(format='%(asctime)s-%(levelname)s-%(message)s', level=logging.INFO, filename='bot.log')
FROM, TO, DATE, SALE = range(4)


def log_error(f):
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print('Ошибка: {}'.format(e))
            raise e
    return inner


@log_error
def start_handler(bot, update):
    update.message.reply_text("Введите название города ИЗ которого вы хотите поехать:",
                              reply_markup=ReplyKeyboardRemove())
    return FROM


@log_error
def from_handler(bot, update, user_data: dict):
    print(update.message.text)
    from_code = get_rzd_info.get_station_code(update.message.text)
    print(from_code)
    if from_code is None:
        update.message.reply_text('Пожалуйста, введите корректный город:')
        return FROM
    else:
        user_data['FROM'] = from_code
        update.message.reply_text("Введите название города В который вы хотите поехать:")
        return TO


@log_error
def to_handler(bot, update, user_data):
    print(update.message.text)
    to_code = get_rzd_info.get_station_code(update.message.text)
    print(to_code)
    if to_code is None:
        update.message.reply_text('Пожалуйста, введите корректный город:')
        return TO
    else:
        user_data['TO'] = to_code
        print(user_data)
        update.message.reply_text("Введите дату поездки в формате ДД.ММ.ГГГГ")
        return DATE


@log_error
def out_tickets(tickets_info: list, k):
    if len(tickets_info) > 0:
        user_text = ''
        if 'brand' in tickets_info[k]:
            user_text = "*Бренд:* {brand} \n".format(**tickets_info[k])
        user_text += """
*Номер поезда:* {number}
*Станция отправления:* {from_station}
*Станция прибытия:* {where_station}
*Время отправления:* {from_time}
*Время прибытия:* {where_time}
*Время в пути:* {timeInWay} \n""".format(**tickets_info[k])
        i = 0
        while i < len(tickets_info[k]['cars']):
            user_text += """
*Тип:* {type}
*Свободные места:* {freeSeats}
*Цена:* {tariff} \n""".format(**tickets_info[k]['cars'][i])
            i += 1
        return user_text


@log_error
def out_all(bot, update, tickets_info: list):
    if len(tickets_info) > 0:
        k = 0
        while k < len(tickets_info):
            update.message.reply_text(out_tickets(tickets_info, k), parse_mode="Markdown")
            k += 1
    else:
        update.message.reply_text('Билеты не найдены. Попробуйте другую дату.')
        return DATE


@log_error
def date_handler(bot, update, user_data):
    checked_dt = get_rzd_info.check_date(update.message.text)
    if checked_dt == True:
        update.message.reply_text('Пожалуйста, введите корректную дату в формате ДД.ММ.ГГГГ')
        return DATE
    else:
        user_data['DATE'] = get_rzd_info.valid_date(update.message.text)
        tickets_info = get_rzd_info.get_info(get_rzd_info.set_params(user_data))
        if len(tickets_info) > 0:
            k = 0
            while k < len(tickets_info):
                update.message.reply_text(out_tickets(tickets_info, k), parse_mode="Markdown")
                k += 1
            mssgtxt = 'Для поиска самых дешевых билетов нажмите /sales для завершения работы с ботом нажмите /cancel'
            sale_text = get_rzd_info.get_sale(tickets_info)
            user_data['SALE'] = sale_text
            inline_buttons = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=value, callback_data=key) for key, value in config.SALE_CONFIG.items()],
                ],
            )
            update.message.reply_text(mssgtxt, reply_markup=inline_buttons)
        else:
            update.message.reply_text('Билеты не найдены. Попробуйте другую дату.')
            return DATE
        return SALE


@log_error
def sale_handler(bot, update, user_data):
    choose = update.callback_query.data
    chat_id = update.callback_query.message.chat.id
    if choose == '1':
        update.callback_query.bot.send_message(chat_id, 'Найден самый дешевый вариант:{}'.format(user_data['SALE']),
                                               parse_mode="Markdown")
    elif choose == '2':
        update.callback_query.bot.send_message(chat_id, 'Работа окончена')
    return ConversationHandler.END


def cancel_handler(bot, update):
    chat_id = update.message.chat.id
    update.send_message(chat_id, 'Отмена. Для начала с нуля нажмите /start')
    return ConversationHandler.END


@log_error
def talking(bot, update):
    user_text = "Привет, {}! Я помогу найти ж/д билеты! Для начала работы напиши /start ".format(
        update.message.chat.first_name)
    logging.info(user_text)
    update.message.reply_text(user_text, reply_markup=ReplyKeyboardRemove())


def text_error(bot, update):
    update.message.reply_text("Ошибка!")


@log_error
def main():
    my_bot = Updater(config.API_KEY, request_kwargs=config.PROXY)
    dp = my_bot.dispatcher
    con_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_handler),
        ],
        states={
            FROM: [
                MessageHandler(Filters.text, from_handler, pass_user_data=True),
            ],
            TO: [
                MessageHandler(Filters.text, to_handler, pass_user_data=True),
            ],
            DATE: [
                MessageHandler(Filters.text, date_handler, pass_user_data=True),
            ],
            SALE: [
                CallbackQueryHandler(sale_handler, pass_user_data=True)
            ],
        },
        fallbacks=[
            MessageHandler(Filters.all, text_error),
            CommandHandler('cancel', cancel_handler),
        ],
    )
    dp.add_handler(con_handler)
    dp.add_handler(MessageHandler(Filters.text, talking))
    my_bot.start_polling()
    my_bot.idle()


if __name__ == "__main__":
    main()
