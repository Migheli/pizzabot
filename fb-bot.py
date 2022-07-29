import os
from functools import partial
import redis
import requests
from flask import Flask, request
from moltin_api_handlers import get_token_dataset, get_file_url, add_product_to_cart, get_cart_items, delete_item_from_cart, get_cart_by_reference, get_product_catalogue, check_token_status
import json
import time
import logging
from cached_menu_handlers import get_categorised_products_set, get_cached_products_by_category_id, categories_id
import functools

logger = logging.getLogger(__name__)

_database = None

def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.environ['REDIS_PASSWORD']
        database_host = os.environ['REDIS_HOST']
        database_port = os.environ['REDIS_PORT']
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def handle_start(sender_id, moltin_token_dataset, message_content, menu):
    target_category_id = os.environ['BASIC_CATEGORY_ID']
    send_menu(sender_id, moltin_token_dataset, target_category_id, menu)
    return 'MENU'


def send_menu(sender_id, moltin_token_dataset, target_category_id, menu):
    # send menu here
    recipient_id = sender_id
    categorised_products = get_categorised_products_set(menu['data'])
    cached_menu = get_cached_products_by_category_id(categorised_products, target_category_id)
    print(f'Кэшированное меню внутри send_menu{cached_menu}')
    elements = get_menu_elements(cached_menu)
    send_gallery(recipient_id, elements)


def handle_menu(sender_id, moltin_token_dataset, message_content, menu):

    print(f'СОДЕРЖАНИЕ СООБЩЕНИЯ {message_content}')
    status, action, payload = message_content.split('::')
    cart_id = f'cart_{sender_id}'
    recipient_id = sender_id

    if status == 'in_menu':
        if action == 'at_cart':
            cart_dataset = get_cart_by_reference(moltin_token_dataset, cart_id)['data']
            cart_price = cart_dataset['meta']['display_price']['with_tax']['amount']
            cart_items = get_cart_items(moltin_token_dataset, cart_id)['data']
            elements = get_cart_menu_elements(cart_items, cart_price)
            send_gallery(recipient_id, elements)
        if action == 'send_category_menu':
            target_category_id = categories_id[payload]
            send_menu(recipient_id, moltin_token_dataset, target_category_id, menu)
        if action == 'add':
            add_product_to_cart(moltin_token_dataset, payload, cart_id)
            send_message(sender_id, 'Товар добавлен в корзину')
        return 'MENU'


    if status == 'in_cart_menu':
        if action == 'add':
            add_product_to_cart(moltin_token_dataset, payload, cart_id)
        if action == 'replace':
            delete_item_from_cart(moltin_token_dataset, cart_id, payload)
        if action == 'to_menu':
            target_category_id = categories_id['basic']
            send_menu(recipient_id, moltin_token_dataset, target_category_id, menu)

        return 'MENU'

    send_message(sender_id, 'Для навигации, пожалуйста, используйте кнопки')

    return "MENU"


def handle_users_reply(sender_id, moltin_token_dataset, message_text, menu):

    moltin_token_dataset = check_token_status(moltin_token_dataset)
    db = get_database_connection()

    type, action, payload = message_text.split('::')


    states_functions = {
        'START': handle_start,
        'MENU': handle_menu,
    }
    recorded_state = db.get(sender_id)
    if not recorded_state or recorded_state.decode("utf-8") not in states_functions.keys():
        user_state = "START"
    else:
       user_state = recorded_state.decode("utf-8")
    if payload == "/start":
        user_state = "START"
    print(user_state)
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, moltin_token_dataset, message_text, menu)
    db.set(sender_id, next_state)


def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


def set_main_img_href(product_dataset, moltin_token_dataset):
    product_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_dataset['relationships']['main_image']['data']['href'] = get_file_url(moltin_token_dataset, product_img_id)


def update_database(db, moltin_token_dataset):
    menu = get_product_catalogue(moltin_token_dataset)
    for product_dataset in menu['data']:
        set_main_img_href(product_dataset, moltin_token_dataset)
    menu = json.dumps(menu)
    db.set('menu', menu)


def get_moltin_changes(db, moltin_token_dataset):
    """
        Вебхук, который обрабатывает уведомления об обновлениях от интеграции Moltin.
        Если произошли обновления - вносит их в БД, попутно добавляя поле 'href' в main_image датасета продуктов,
        Это поле содержит сведения о URL главного изображения продукта и сокращает в дальнейшем запросы к Moltin.
    """
    moltin_token_dataset = check_token_status(moltin_token_dataset)
    data = request.get_json()
    if data.get("integration"):
        print(f"Сработала интеграция {data['integration']}")
        if data['integration']['id'] == os.environ["MOLTIN_WEBHOOK_INTEGRATION_ID"]:
            print(f"Сработала проверка интеграции {data['integration']}")
            update_database(db, moltin_token_dataset)


            return "ok", 200

    return "Hello world", 200


def facebook_webhook(db, moltin_token_dataset):

    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """

    moltin_token_dataset = check_token_status(moltin_token_dataset)
    menu = json.loads(db.get('menu'))
    data = request.get_json()

    if data["object"] == "page":
        print(f"Сработала страница")
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                print(entry["messaging"])
                sender_id = messaging_event["sender"]["id"]
                #db.set(sender_id, "START")
                if (sender_id == '5304713252982644') and not (messaging_event.get('delivery') or messaging_event.get('read')):
                    print('Сработало сообщение от пользователя')
                    if messaging_event.get("message"):
                        message_content = f'text_message::0::{messaging_event["message"]["text"]}'
                    if messaging_event.get('postback'):
                        message_content = messaging_event['postback']['payload']
                    print(message_content)
                    handle_users_reply(sender_id, moltin_token_dataset, message_content, menu)
    return "ok", 200


def send_message(recipient_id, message_text):
    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    headers = {"Content-Type": "application/json"}
    request_content = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    response = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers,
                             data=request_content)
    response.raise_for_status()


def get_main_menu():
    return {
        "title": "Меню",
        "image_url": os.environ["PIZZERIA_LOGO_URL"],
        "subtitle": "Здесь можно выбрать один из вариантов",
        "default_action": {
            "type": "web_url",
            "url": os.environ["PIZZERIA_LOGO_URL"],
            "webview_height_ratio": "compact",
        },
        "buttons": [
            {
                "type": "postback",
                "title": "Сделать заказ",
                "payload": "in_menu::make_order::0"
            },
            {
                "type": "postback",
                "title": "Корзина",
                "payload": "in_menu::at_cart::0"
            },
            {
                "type": "postback",
                "title": "Акции",
                "payload": "in_menu::promo::0"
            }
        ]
    }

def get_categories_menu():
    return {
        "title": "Не нашли нужную пиццу?",
        "image_url": os.environ["CATEGORIES_LOGO_URL"],
        "subtitle": "Здесь можно выбрать один из вариантов",
        "default_action": {
            "type": "web_url",
            "url": os.environ["PIZZERIA_LOGO_URL"],
            "webview_height_ratio": "compact",
        },
        "buttons": [
            {
                "type": "postback",
                "title": "Острые",
                "payload": f"in_menu::send_category_menu::spicy"
            },
            {
                "type": "postback",
                "title": "Сытные",
                "payload": f"in_menu::send_category_menu::nutritious"
            },
            {
                "type": "postback",
                "title": "Особые",
                "payload": f"in_menu::send_category_menu::specials"
            }
        ]
    }


def get_serialized_product_dataset(product_dataset):

    product_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_img_url = product_dataset['relationships']['main_image']['data']['href']
    print(product_dataset)
    serialize_product_dataset = {
        "title": f"{product_dataset['name']} ({product_dataset['price'][0]['amount']} руб.)",
        "image_url": product_img_url,
        "subtitle": product_dataset['description'],
        "default_action": {
            "type": "web_url",
            "url": "https://www.originalcoastclothing.com/",
            "webview_height_ratio": "compact",
        },
        "buttons": [
                      {
                        "type":"postback",
                        "title":"В корзину",
                        "payload": f"in_menu::add::{product_dataset['id']}"
                      }
        ]
    }

    return serialize_product_dataset


def get_serialized_cart_item_dataset(product_dataset):

    print(product_dataset)
    serialize_product_dataset = {
        "title": f"{product_dataset['name']}. В корзине: {product_dataset['quantity']} шт.",
        "image_url": product_dataset['image']['href'],
        "subtitle": f"{product_dataset['description']}",
        "default_action": {
            "type": "web_url",
            "url": "https://www.originalcoastclothing.com/",
            "webview_height_ratio": "compact",
        },
        "buttons": [
                      {
                        "type":"postback",
                        "title":"Добавить еще одну",
                        "payload": f"in_cart_menu::add::{product_dataset['product_id']}"
                      },

                      {
                          "type": "postback",
                          "title": "Удалить из корзины",
                          "payload": f"in_cart_menu::replace::{product_dataset['id']}"
                      },

        ]
    }

    return serialize_product_dataset

def get_cart_page(cart_price):
    return {
        "title": "Корзина",
        "image_url": os.environ["CART_LOGO_URL"],
        "subtitle": f"Ваш заказ на сумму {cart_price}",
        "default_action": {
            "type": "web_url",
            "url": os.environ["PIZZERIA_LOGO_URL"],
            "webview_height_ratio": "compact",
        },
        "buttons": [
            {
                "type": "postback",
                "title": "Самовывоз",
                "payload": "in_cart_menu::self-delivery::0"
            },
            {
                "type": "postback",
                "title": "Доставка",
                "payload": "in_cart_menu::delivery::0"
            },
            {
                "type": "postback",
                "title": "К меню",
                "payload": "in_cart_menu::to_menu::0"
            }
        ]
    }


def get_cart_menu_elements(cart_items, cart_price):
    elements = []
    elements.append(get_cart_page(cart_price))
    for cart_item in cart_items:
        serialized_product_dataset = get_serialized_cart_item_dataset(cart_item)
        elements.append(serialized_product_dataset)
    return elements


def send_gallery(recipient_id, elements):

    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    headers = {"Content-Type": "application/json"}

    request_content = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements,
                }
            }
        }
    }

    response = requests.post(
        'https://graph.facebook.com/v2.6/me/messages',
        params=params,
        headers=headers,
        json=request_content
    )
    response.raise_for_status()

def get_menu_elements(catalogue):
    elements = []
    elements.append(get_main_menu())
    for product_dataset in catalogue:
        serialized_product_dataset = get_serialized_product_dataset(product_dataset)
        elements.append(serialized_product_dataset)
    elements.append(get_categories_menu())
    return elements

def facebook_handler_wrapper():
    return

def moltin_changes_handler_wrapper():
    return


def main():
    logging.basicConfig(format='FB-bot: %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    while True:
        try:
            app = Flask(__name__)
            db = get_database_connection()
            moltin_token_dataset = get_token_dataset()

            facebook_handler = partial(facebook_webhook, db=db, moltin_token_dataset=moltin_token_dataset)
            moltin_changes_handler = partial(get_moltin_changes, db=db, moltin_token_dataset=moltin_token_dataset)
            functools.update_wrapper(facebook_handler, facebook_handler_wrapper)
            functools.update_wrapper(moltin_changes_handler, moltin_changes_handler_wrapper)
            app.add_url_rule('/', view_func=verify, methods=['GET'])
            app.add_url_rule('/', view_func=facebook_handler, methods=['POST'])
            app.add_url_rule('/changes_checker', view_func=moltin_changes_handler, methods=['POST'])

            app.run(debug=True)

        except Exception as err:
            logging.error('Facebook бот упал с ошибкой:')
            logging.exception(err)


if __name__ == '__main__':
    main()
