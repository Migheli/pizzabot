import os
from functools import partial
import redis
import requests
from flask import Flask, request
from moltin_api_handlers import get_token_dataset, get_file_url, add_product_to_cart, get_cart_items, delete_item_from_cart, get_cart_by_reference, get_product_catalogue
import json
import time
import logging
from cached_menu_handlers import get_categorised_products_set, get_cached_products_by_category_id, categories_id


app = Flask(__name__)

MOLTIN_TOKEN_DATASET = get_token_dataset()
MENU = json.dumps(get_product_catalogue(MOLTIN_TOKEN_DATASET))
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

DB = get_database_connection()
#DB.set('menu', MENU)


def check_token_status(moltin_token_dataset):
    """
    Проверяет актуальность токена по времени его действия и, в случае необходимости, обновляет его.
    """
    if int(time.time()) >= moltin_token_dataset['expires']:
        moltin_token_dataset = get_token_dataset()
    return moltin_token_dataset


#get_category_id_by_slug('basic', moltin_token_dataset)

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
    elements = get_menu_elements(cached_menu, moltin_token_dataset)
    send_gallery_new(recipient_id, elements)


def handle_menu(sender_id, moltin_token_dataset, message_content, menu):

    print(f'СОДЕРЖАНИЕ СООБЩЕНИЯ {message_content}')
    print(menu)
    cart_id = f'cart_{sender_id}'
    recipient_id = sender_id

    if message_content == 'to_menu':
        send_menu(recipient_id, moltin_token_dataset, 'basic')


    if 'in_cart' in message_content :
        in_cart, command, product_id = message_content.split('::')
        print(command)
        if command == 'replace':
            delete_item_from_cart(moltin_token_dataset, cart_id, product_id)
        if command == 'add':
            print(product_id, cart_id)
            add_product_to_cart(moltin_token_dataset, product_id, cart_id)



    if message_content=='at_cart':
        cart_dataset = get_cart_by_reference(moltin_token_dataset, cart_id)['data']
        cart_price = cart_dataset['meta']['display_price']['with_tax']['amount']

        cart_items = get_cart_items(moltin_token_dataset, cart_id)['data']
        elements = get_cart_menu_elements(cart_items, cart_price)
        recipient_id = sender_id
        send_gallery_new(recipient_id, elements)


    if 'category' in message_content:
        command, page_category_slug = message_content.split('::')
        target_category_id = categories_id[page_category_slug]
        send_menu(recipient_id, moltin_token_dataset, target_category_id, menu)
        return "MENU"

    if 'to_cart' in message_content:
        command, product_id = message_content.split('::')
        print(product_id, cart_id)
        add_product_to_cart(moltin_token_dataset, product_id, cart_id)
        send_message(sender_id, 'Товар добавлен в корзину')
        return "MENU"

    send_message(sender_id, 'Сообщение в ответ на сообщение из статуса MENU')

    return "MENU"


def handle_users_reply(sender_id, moltin_token_dataset, message_text, menu):

    moltin_token_dataset = check_token_status(moltin_token_dataset)
    db = get_database_connection()


    webhook_url = os.environ["NGROK_FORWARDING_URL"]
    #integration_id = get_integration_webhook(webhook_url, moltin_token_dataset)['data']['id']
    #integration_id = os.environ["MOLTIN_WEBHOOK_INTEGRATION_ID"]
    #print(integration_id)

    states_functions = {
        'START': handle_start,
        'MENU': handle_menu,
    }
    recorded_state = db.get(sender_id)
    if not recorded_state or recorded_state.decode("utf-8") not in states_functions.keys():
        user_state = "START"
    else:
       user_state = recorded_state.decode("utf-8")
    if message_text == "/start":
        user_state = "START"
    print(user_state)
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, moltin_token_dataset, message_text, menu)
    db.set(sender_id, next_state)



@app.route('/', methods=['GET'])
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



@app.route('/changes_checker', methods=['POST'])
def check_moltin_changes():
    moltin_token_dataset = check_token_status(MOLTIN_TOKEN_DATASET)

    data = request.get_json()
    if data.get("integration"):
        print(f"Сработала интеграция {data['integration']}")
        if data['integration']['id'] == os.environ["MOLTIN_WEBHOOK_INTEGRATION_ID"]:
            print(f"Сработала проверка интеграции {data['integration']}")

            menu = get_product_catalogue(moltin_token_dataset)
            for product_dataset in menu['data']:
                set_main_img_href(product_dataset, moltin_token_dataset)

            menu = json.dumps(menu)

            DB.set('menu', menu)
            return "ok", 200

    return "Hello world", 200





@app.route('/', methods=['POST'])
def webhook():


    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """

    moltin_token_dataset = check_token_status(MOLTIN_TOKEN_DATASET)
    print(f'Произошло обновление токена {moltin_token_dataset["access_token"]}')

    menu = json.loads(DB.get('menu'))
    #for product_dataset in menu['data']:
    #    set_main_img_href(product_dataset, moltin_token_dataset)


    print(menu['data'][0])
    data = request.get_json()
    '''
    if data.get("integration"):
        print(f"Сработала интеграция {data['integration']}")
        if data['integration']['id'] == os.environ["MOLTIN_WEBHOOK_INTEGRATION_ID"]:
            print(f"Сработала проверка интеграции {data['integration']}")

            menu = get_product_catalogue(moltin_token_dataset)
            new_menu = json.dumps(menu)

            for product_dataset in new_menu['data']:
                set_main_img_href(product_dataset, moltin_token_dataset)

            DB.set('menu', new_menu)
            return "ok", 200

    #db = get_database_connection()
    #handle_users_reply_token_prefilled = partial(handle_users_reply, moltin_token_dataset=moltin_token_dataset)
    #print(data["object"])
    '''
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
                        message_content = messaging_event["message"]["text"]
                    if messaging_event.get('postback'):
                        message_content = messaging_event['postback']['payload']
                    print(message_content)
                    handle_users_reply(sender_id, moltin_token_dataset, message_content, menu)
    return "ok", 200

def create_or_update_menu(moltin_token_dataset):
    db = get_database_connection()



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
                "payload": "make_order"
            },
            {
                "type": "postback",
                "title": "Корзина",
                "payload": "at_cart"
            },
            {
                "type": "postback",
                "title": "Акции",
                "payload": "promo"
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
                "payload": f"category::spicy"
            },
            {
                "type": "postback",
                "title": "Сытные",
                "payload": f"category::nutritious"
            },
            {
                "type": "postback",
                "title": "Особые",
                "payload": f"category::specials"
            }
        ]
    }


def get_serialized_product_dataset(product_dataset, moltin_token_dataset):

    product_img_id = product_dataset['relationships']['main_image']['data']['id']
    #product_img_url = get_file_url(moltin_token_dataset, product_img_id)
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
                        "payload": f"to_cart::{product_dataset['id']}"
                      }
        ]
    }

    return serialize_product_dataset



def get_serialized_product_dataset(product_dataset, moltin_token_dataset):

    product_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_img_url = get_file_url(moltin_token_dataset, product_img_id)

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
                        "payload": f"to_cart::{product_dataset['id']}"
                      }
        ]
    }
    print(serialize_product_dataset)
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
                        "payload": f"in_cart::add::{product_dataset['product_id']}"
                      },

                      {
                          "type": "postback",
                          "title": "Удалить из корзины",
                          "payload": f"in_cart::replace::{product_dataset['id']}"
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
                "payload": "self"
            },
            {
                "type": "postback",
                "title": "Доставка",
                "payload": "delivery"
            },
            {
                "type": "postback",
                "title": "К меню",
                "payload": "to_menu"
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


def send_gallery_new(recipient_id, elements):

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

def get_menu_elements(catalogue, moltin_token_dataset):
    elements = []
    elements.append(get_main_menu())
    for product_dataset in catalogue:
        serialized_product_dataset = get_serialized_product_dataset(product_dataset, moltin_token_dataset)
        elements.append(serialized_product_dataset)
    elements.append(get_categories_menu())
    return elements




if __name__ == '__main__':
    app.run(debug=True)