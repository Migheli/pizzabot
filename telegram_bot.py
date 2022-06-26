import logging
import os
import time
from functools import partial
import requests
from telegram import LabeledPrice
import redis
from textwrap import dedent
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext, PreCheckoutQueryHandler

from keyboards import get_product_keyboard, get_multipage_keyboard, get_delivery_type_keyboard, get_handle_menu_keyboard
from location_handlers import get_nearest_entry, get_location
from moltin_api_handlers import get_all_entries, get_entry_by_id,  get_product_catalogue, get_product_by_id, \
    add_product_to_cart, get_cart_items, delete_item_from_cart, serialize_products_datasets, get_token_dataset, \
    get_file_url
from flow_creator import create_new_customer


logger = logging.getLogger(__name__)

_database = None
MAX_PRODUCTS_PER_PAGE = int(os.getenv('MAX_PRODUCTS_PER_PAGE'))
YANDEX_GEOCODER_KEY = os.getenv('YANDEX_GEOCODER_KEY')


def get_products_datasets(products, max_products_per_page):
    for product in range(0, len(products), max_products_per_page):
        yield products[product:product + max_products_per_page]


def serialize_products_catalogue(products, max_products_per_page):
    products_datasets = list(get_products_datasets(products, max_products_per_page))
    return products_datasets


def fetch_coordinates(YANDEX_GEOCODER_KEY, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": YANDEX_GEOCODER_KEY,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def show_main_menu(update: Update, context: CallbackContext, moltin_token, index_of_page=0):
    products = get_product_catalogue(moltin_token)['data']

    if len(products) > MAX_PRODUCTS_PER_PAGE:
        products_datasets = serialize_products_catalogue(products, MAX_PRODUCTS_PER_PAGE)
        keyboard = get_multipage_keyboard(products_datasets, index_of_page)
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in products]
        reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='*Пожалуйста, выберите товар:*',
                                 parse_mode=constants.PARSEMODE_MARKDOWN_V2,
                                 reply_markup=reply_markup)
    return 'HANDLE_MENU'


def show_cart_menu(update: Update, context: CallbackContext, moltin_token):

    chat_id = update.effective_chat.id
    cart_items = get_cart_items(moltin_token, chat_id)
    products_in_cart = cart_items['data']
    reply_markup = get_product_keyboard(products_in_cart)
    cart_items_text = serialize_products_datasets(cart_items)
    context.bot.send_message(chat_id=chat_id,
                             text=cart_items_text,
                             reply_markup=reply_markup
                             )


def handle_menu(update: Update, context: CallbackContext, moltin_token):

    if 'show_products_page' in update.callback_query.data:
        text, index_of_page = update.callback_query.data.split('::')
        product_dataset = get_product_catalogue(moltin_token)['data']
        serialized_products_datasets = serialize_products_catalogue(product_dataset, MAX_PRODUCTS_PER_PAGE)
        keyboard = get_multipage_keyboard(serialized_products_datasets, index_of_page)
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                              message_id = update.callback_query['message']['message_id'],
                                              reply_markup=reply_markup)
        return 'HANDLE_MENU'

    if update.callback_query.data == 'at_cart':
        show_cart_menu(update, context, moltin_token)
        return 'HANDLE_CART'

    product_id = update.callback_query.data

    keyboard = get_handle_menu_keyboard(product_id)

    product_dataset = get_product_by_id(moltin_token, product_id)['data']
    chat_id = update.effective_chat.id
    message_id = update.callback_query['message']['message_id']

    reply_markup = InlineKeyboardMarkup(keyboard)

    product_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_img_url = get_file_url(moltin_token, product_img_id)

    cart_items = get_cart_items(moltin_token, chat_id)
    products_in_cart = cart_items['data']
    quantity_in_cart = 0

    for product_in_cart in products_in_cart:
        if product_in_cart['product_id'] == product_id:
            quantity_in_cart = product_in_cart['quantity']


    context.bot.send_photo(chat_id=chat_id,
                           photo=product_img_url,
                           caption=dedent(f"""\
                           Предлагаем Вашему вниманию: {product_dataset['name']}
                           Цена: {product_dataset['price'][0]['amount']}{product_dataset['price'][0]['currency']}
                           Описание товара: {product_dataset['description']}
                           Уже в корзине: {quantity_in_cart}
                           """),
                           reply_markup=reply_markup
                           )
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)

    return 'HANDLE_DESCRIPTION'


def handle_description(update: Update, context: CallbackContext, moltin_token):

    message_id = update.callback_query['message']['message_id']
    chat_id = update.effective_chat.id
    if update.callback_query.data == 'back':
        show_main_menu(update, context, moltin_token)
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return 'HANDLE_MENU'

    if update.callback_query.data == 'at_cart':
        show_cart_menu(update, context, moltin_token)
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return 'HANDLE_CART'

    product_id = update.callback_query.data
    product_dataset = get_product_by_id(moltin_token, product_id)
    product_name = product_dataset['data']['name']

    try:
        add_product_to_cart(moltin_token, product_id, chat_id)
        update.callback_query.answer(f'{product_name} добавлено в корзину', show_alert=True)

        cart_items = get_cart_items(moltin_token, chat_id)
        products_in_cart = cart_items['data']
        quantity_in_cart = 0

        for product_in_cart in products_in_cart:
            if product_in_cart['product_id'] == product_id:
                quantity_in_cart = product_in_cart['quantity']

        keyboard = get_handle_menu_keyboard(product_id)
        reply_markup = InlineKeyboardMarkup(keyboard)

        product_dataset = get_product_by_id(moltin_token, product_id)['data']
        chat_id = update.effective_chat.id
        message_id = update.callback_query['message']['message_id']

        context.bot.edit_message_caption(chat_id=chat_id, message_id = message_id,
                               caption=dedent(f"""\
                                   Предлагаем Вашему вниманию: {product_dataset['name']}
                                   Цена: {product_dataset['price'][0]['amount']}{product_dataset['price'][0]['currency']}
                                   Описание товара: {product_dataset['description']}
                                   Уже в корзине: {quantity_in_cart}
                                   """),
                               reply_markup=reply_markup
                               )

    except Exception as error:
        logging.error(f'{error}')
        update.callback_query.answer(f'Возникли проблемы с добавлением товара в корзину', show_alert=True)


def handle_cart(update: Update, context: CallbackContext, moltin_token):
    message_id = update.callback_query['message']['message_id']
    if update.callback_query.data == 'at_payment':
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Пожалуйста, введите Ваш адрес или отправьте геопозицию')
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        return 'HANDLE_LOCATION'

    if update.callback_query.data == 'back':
        show_main_menu(update, context, moltin_token)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        return 'HANDLE_MENU'

    cart_id = update.effective_chat.id
    cart_item_id = update.callback_query.data
    delete_item_from_cart(moltin_token, cart_id, cart_item_id)
    update.callback_query.answer(f'Товар удален из корзины', show_alert=True)

    cart_items = get_cart_items(moltin_token, cart_id)
    products_in_cart = cart_items['data']
    reply_markup = get_product_keyboard(products_in_cart)
    cart_items_text = serialize_products_datasets(cart_items)

    context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                  message_id=update.callback_query['message']['message_id'],
                                  reply_markup=reply_markup,
                                  text=cart_items_text
                                  )





def handle_customer_location(update: Update, context: CallbackContext, moltin_token):

    min_distance_to_customer = None
    restaurants_flow_slug = os.getenv('RESTAURANTS_FLOW_SLUG')
    if update.message.location:
        customer_coordinates = get_location(update)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f'Ваше местоположение - {str(customer_coordinates)}')
        restaurants_entries = get_all_entries(moltin_token, restaurants_flow_slug)
        nearest_entry = get_nearest_entry(restaurants_entries, customer_coordinates)
        nearest_entry_address = nearest_entry['address']
        nearest_entry_id = nearest_entry['id']
        min_distance_to_customer = nearest_entry['distance_to_customer']
        longitude, latitude = get_location(update)
        customer_id = create_new_customer(moltin_token, 'customer_address', longitude, latitude)['id']

    text_of_message = update.message.text
    customer_coordinates = fetch_coordinates(YANDEX_GEOCODER_KEY, text_of_message)

    if customer_coordinates:
        longitude, latitude = customer_coordinates
        customer_id = create_new_customer(moltin_token, 'customer_address', longitude, latitude)['id']
        entries = get_all_entries(moltin_token, restaurants_flow_slug)
        nearest_entry = get_nearest_entry(entries, customer_coordinates)
        nearest_entry_address = nearest_entry['address']
        nearest_entry_id = nearest_entry['id']
        min_distance_to_customer = nearest_entry['distance_to_customer']

    if min_distance_to_customer:

        keyboard = get_delivery_type_keyboard(nearest_entry_id, longitude, latitude)
        serialized_min_distance_to_customer = int(min_distance_to_customer*1000)

        if min_distance_to_customer <= 0.5:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=dedent(f"""\
                                     Может, хотите забрать пиццу сами из нашей пиццерии неподалеку? 
                                     Она всего в {serialized_min_distance_to_customer} м от Вас по адресу:
                                     {nearest_entry_address} 
                                     Можем и бесплатно привезти , нам не сложно:)"""
                                                 ),
                                     reply_markup=InlineKeyboardMarkup(keyboard)
                                     )

        if min_distance_to_customer <= 5 and min_distance_to_customer > 0.5:
            shipping_cost = 100
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=dedent(f"""\
                                     Придется ехать до Вас на велосипеде. 
                                     Доставка будет стоить всего {shipping_cost} рублей. """
                                                 ),
                                     reply_markup=InlineKeyboardMarkup(keyboard)
                                     )

        if min_distance_to_customer <= 20 and min_distance_to_customer > 5:
            shipping_cost = 300
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=dedent(f""" Мы можем доставить пиццу. 
                                                      Доставка будет стоить: {shipping_cost} рублей.
                                                  """
                                                 ),
                                     reply_markup=InlineKeyboardMarkup(keyboard)
                                     )
        if min_distance_to_customer > 20:
            serialized_min_distance_to_customer = int(min_distance_to_customer)
            keyboard = [InlineKeyboardButton(text='Заберу сам',
                                             callback_data=f'self::{nearest_entry_id}::{longitude}::{latitude}')],
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=dedent(f"""
                                     Простите, но так далеко мы пиццу доставить не сможем. 
                                     Ближайшая пиццерия в {serialized_min_distance_to_customer} км от Вас!
                                     Но Вы можете оплатить пиццу и забрать ее самостоятельно.
                                     """),
                                     reply_markup=InlineKeyboardMarkup(keyboard)
                                     )
        return 'HANDLE_DELIVERY_METHOD'

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=dedent(f"""
                                                Простите, но я так не смогу распознать Ваше местоположение.
                                                Попробуйте еще раз: отправьте адрес или геопозицию.
                                                """),
                             )
    return 'HANDLE_LOCATION'


def handle_delivery_method(update: Update, context: CallbackContext, moltin_token_dataset):
    delivery_method, nearest_entry_id, longitude, latitude = update.callback_query.data.split('::')
    if delivery_method == 'shpg':
        nearest_entry_dataset = get_entry_by_id(moltin_token_dataset, 'pizza25', str(nearest_entry_id))
        deliveryman_tg_id = nearest_entry_dataset['deliveryman_id']
        context.bot.send_location(chat_id=deliveryman_tg_id, latitude=latitude, longitude=longitude)

        chat_id = update.effective_chat.id
        cart_items = get_cart_items(moltin_token_dataset, chat_id)
        products_in_cart = cart_items['data']
        cart_items_text = serialize_products_datasets(cart_items)
        context.bot.send_message(chat_id=deliveryman_tg_id,
                                 text=cart_items_text)

        order_reminder(update, context)
        payment_callback(update, context)
        precheckout_callback(update, context)

    if update.callback_query.data == 'self':
        context.bot.send_message(chat_id=deliveryman_tg_id,
                                 text=dedent("""
                                            Приятного аппетита! *место для рекламы*
                                            *сообщение что делать если пицца не пришла*
                                            """))


def check_token_status(moltin_token_dataset):
    """
    Проверяет актуальность токена по времени его действия и, в случае необходимости, обновляет его.
    """
    if int(time.time()) >= moltin_token_dataset['expires']:
        moltin_token_dataset = get_token_dataset()
    return moltin_token_dataset


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.getenv('REDIS_PASSWORD')
        database_host = os.getenv('REDIS_HOST')
        database_port = os.getenv('REDIS_PORT')
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def after_order_message(context):
    context.bot.send_message(context.job.context, text=dedent
    ("""
    Приятного аппетита! *место для рекламы*
    *сообщение что делать если пицца не пришла*
    """)
                             )

def order_reminder(update, context):
    context.job_queue.run_once(after_order_message, 10, context=update.effective_chat.id)



def payment_callback(update, context):
    chat_id = update.effective_chat.id
    title = "Payment Example"
    description = "Payment Example using python-telegram-bot"
    payload = "my_payload"
    provider_token = os.getenv('PAYMENT_TOKEN')
    price = 1
    prices = [LabeledPrice("Test", price * 100)]
    context.bot.sendInvoice(chat_id=chat_id, title=title, description=description, payload=payload,
                    provider_token=provider_token, currency="RUB", prices=prices)


def precheckout_callback(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    if query.invoice_payload != "my_payload":
        return query.answer(ok=False, error_message="Something went wrong...")
    else:
        return query.answer(ok=True)


def handle_users_reply(update: Update, context: CallbackContext, moltin_token_dataset):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    moltin_token_dataset = check_token_status(moltin_token_dataset)
    db = get_database_connection()
    chat_id = update.effective_chat.id
    if update.message:
        user_reply = update.message.text
    elif update.callback_query:
        user_reply = update.callback_query.data
    elif update.pre_checkout_query:
        user_reply = update.pre_checkout_query
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': show_main_menu,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'HANDLE_LOCATION': handle_customer_location,
        'HANDLE_DELIVERY_METHOD': handle_delivery_method,
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context, moltin_token_dataset)
    if next_state:
        db.set(chat_id, next_state)


def main():

    logging.basicConfig(format='TG-bot: %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)



    while True:
        try:
            moltin_token_dataset = get_token_dataset()
            handle_users_reply_token_prefilled = partial(handle_users_reply, moltin_token_dataset=moltin_token_dataset)
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            updater = Updater(token, use_context=True)


            logger.info('Бот в Telegram успешно запущен')
            dispatcher = updater.dispatcher
            dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_token_prefilled))
            dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply_token_prefilled))
            dispatcher.add_handler(MessageHandler(Filters.location, handle_users_reply_token_prefilled))
            dispatcher.add_handler(CommandHandler('start', handle_users_reply_token_prefilled))
            dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))

            updater.start_polling()
            updater.idle()

        except Exception as err:
            logging.error('Телеграм бот упал с ошибкой:')
            logging.exception(err)


if __name__ == '__main__':
    main()
