import os
import json
from logging.handlers import RotatingFileHandler
import logging
from functools import partial, update_wrapper
import redis
from flask import Flask, request

from moltin_api_handlers import get_token_dataset, add_product_to_cart, \
    get_cart_items, delete_item_from_cart, get_cart_by_reference, \
    check_token_status
from cached_menu_handlers import get_categorised_products_set, \
    get_cached_products_by_category_id, categories_id, update_database
from fb_requests_handlers import send_message, send_gallery, get_menu_elements,\
    get_cart_menu_elements
from handlers_wrappers import facebook_handler_wrapper,\
    moltin_changes_handler_wrapper, cart_managment_wrapper


logger = logging.getLogger(__name__)

_database = None


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый,
    если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.environ["REDIS_PASSWORD"]
        database_host = os.environ["REDIS_HOST"]
        database_port = os.environ["REDIS_PORT"]
        _database = redis.Redis(
            host=database_host,
            port=database_port,
            password=database_password
        )
    return _database


def handle_start(sender_id, moltin_token_dataset, message_content, menu):
    target_category_id = os.environ["BASIC_CATEGORY_ID"]
    send_menu_by_category(sender_id, target_category_id, menu)
    return "MENU"


def send_menu_by_category(sender_id, target_category_id, menu):
    recipient_id = sender_id
    categorised_products = get_categorised_products_set(menu["data"])
    cached_menu = get_cached_products_by_category_id(categorised_products, target_category_id)
    elements = get_menu_elements(cached_menu)
    send_gallery(recipient_id, elements)


def handle_menu(sender_id, moltin_token_dataset, message_content, menu):
    status, action, payload = message_content.split("::")
    cart_id = f"cart_{sender_id}"
    recipient_id = sender_id

    if status == "in_menu":
        if action == "at_cart":
            cart_dataset = get_cart_by_reference(moltin_token_dataset, cart_id)["data"]
            cart_price = cart_dataset["meta"]["display_price"]["with_tax"]["amount"]
            cart_items = get_cart_items(moltin_token_dataset, cart_id)["data"]
            elements = get_cart_menu_elements(cart_items, cart_price)
            send_gallery(recipient_id, elements)
        if action == "send_category_menu":
            target_category_id = categories_id[payload]
            send_menu_by_category(recipient_id, target_category_id, menu)
        if action == "add":
            cart_managment_wrapper(add_product_to_cart, moltin_token_dataset, payload, cart_id, sender_id)

        return "MENU"

    if status == "in_cart_menu":
        if action == "add":
            cart_managment_wrapper(add_product_to_cart, moltin_token_dataset, payload, cart_id, sender_id)
        if action == "replace":
            cart_managment_wrapper(delete_item_from_cart, moltin_token_dataset, payload, cart_id, sender_id)
        if action == "to_menu":
            target_category_id = categories_id["basic"]
            send_menu_by_category(recipient_id, target_category_id, menu)

        return "MENU"

    send_message(sender_id, "Для навигации, пожалуйста, используйте кнопки")

    return "MENU"


def handle_users_reply(sender_id, moltin_token_dataset, message_content, menu):
    moltin_token_dataset = check_token_status(moltin_token_dataset)
    db = get_database_connection()
    type, action, payload = message_content.split("::")

    states_functions = {
        "START": handle_start,
        "MENU": handle_menu,
    }
    recorded_state = db.get(sender_id)
    if not recorded_state or recorded_state.decode("utf-8") \
            not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state.decode("utf-8")
    if payload == "/start":
        user_state = "START"
    state_handler = states_functions[user_state]
    next_state = state_handler(
        sender_id=sender_id,
        moltin_token_dataset=moltin_token_dataset,
        message_content=message_content,
        menu=menu
    )
    db.set(sender_id, next_state)


def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес.
    На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


def get_moltin_changes(db, moltin_token_dataset):
    """
        Вебхук, который обрабатывает уведомления об обновлениях от интеграции
        Moltin.
        Если произошли обновления - вносит их в БД, попутно добавляя поле 'href'
        в main_image датасета продуктов,
        Это поле содержит сведения о URL главного изображения продукта и
        сокращает в дальнейшем запросы к Moltin.
    """
    moltin_token_dataset = check_token_status(moltin_token_dataset)
    data = request.get_json()
    if not data.get("integration"):
        return "Incorrect request", 400
    if data["integration"]["id"] == os.environ["MOLTIN_WEBHOOK_INTEGRATION_ID"]:
        update_database(db, moltin_token_dataset)
    return "Ok", 200


def facebook_webhook(db, moltin_token_dataset):

    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """

    moltin_token_dataset = check_token_status(moltin_token_dataset)
    menu = json.loads(db.get('menu'))
    data = request.get_json()

    if not data["object"] == "page":
        return "Incorrect request", 400

    for entry in data["entry"]:
        for messaging_event in entry["messaging"]:
            sender_id = messaging_event["sender"]["id"]

            # проверяем не было ли сообщение отправлено самим ботом
            # и не является ли оно отчетом о доставке или прочтении
            is_self_message = sender_id == os.environ["FB_BOT_ID"]
            if any(messaging_event.get("delivery"), messaging_event.get("read"), is_self_message):
                return "non-processing event", 200

            if messaging_event.get("message"):
                message_content = f'text_message::0::{messaging_event["message"]["text"]}'
            if messaging_event.get("postback"):
                message_content = messaging_event["postback"]["payload"]

            handle_users_reply(
                sender_id=sender_id,
                moltin_token_dataset=moltin_token_dataset,
                message_content=message_content,
                menu=menu)

    return "ok", 200


def main():

    app = Flask(__name__)

    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/fb-bot.log', maxBytes=10240,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    db = get_database_connection()
    moltin_token_dataset = get_token_dataset()

    facebook_handler = partial(
        facebook_webhook,
        db=db,
        moltin_token_dataset=moltin_token_dataset
    )
    moltin_changes_handler = partial(
        get_moltin_changes,
        db=db,
        moltin_token_dataset=moltin_token_dataset)
    update_wrapper(facebook_handler, facebook_handler_wrapper)
    update_wrapper(moltin_changes_handler, moltin_changes_handler_wrapper)
    app.add_url_rule('/', view_func=verify, methods=["GET"])
    app.add_url_rule('/', view_func=facebook_handler, methods=["POST"])
    app.add_url_rule('/changes_checker', view_func=moltin_changes_handler,
                     methods=["POST"])
    app.run(debug=True)
    app.logger.info('Facebook-bot startup')

if __name__ == "__main__":
    main()
