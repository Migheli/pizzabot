import os
from functools import partial
import redis
import requests
from flask import Flask, request
from moltin_api_handlers import get_token_dataset, get_file_url, add_product_to_cart, get_cart_items, delete_item_from_cart, get_cart_by_reference
import json

import logging

app = Flask(__name__)
FACEBOOK_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]

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


def handle_start(sender_id, moltin_token_dataset, page_category_slug=None):
    # send menu here
    if page_category_slug is None:
        page_category_slug = 'basic'
    target_category_id = get_category_id_by_slug(page_category_slug, moltin_token_dataset)
    catalogue = get_products_by_category_id(target_category_id, moltin_token_dataset)['data']
    print('Сработал')

    send_gallery(sender_id, catalogue, moltin_token_dataset)
    return "MENU"

def handle_menu(sender_id, moltin_token_dataset, message_content):

    cart_id = f'cart_{sender_id}'


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
        target_category_id = get_category_id_by_slug(page_category_slug, moltin_token_dataset)
        catalogue = get_products_by_category_id(target_category_id, moltin_token_dataset)['data']
        send_gallery(sender_id, catalogue, moltin_token_dataset)
        return "MENU"

    if 'to_cart' in message_content:
        command, product_id = message_content.split('::')
        print(product_id, cart_id)
        add_product_to_cart(moltin_token_dataset, product_id, cart_id)
        send_message(sender_id, 'Товар добавлен в корзину')
        return "MENU"

    return "MENU"


def handle_users_reply(sender_id, moltin_token_dataset, message_text):

    db = get_database_connection()

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
    next_state = state_handler(sender_id, moltin_token_dataset, message_text)
    db.set(sender_id, next_state)


print(os.environ["VERIFY_TOKEN"])

@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    logging.warning(request.args.get("hub.verify_token"))
    logging.warning(os.environ["VERIFY_TOKEN"])
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200



@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()

    #db = get_database_connection()
    moltin_token_dataset = get_token_dataset()
    #handle_users_reply_token_prefilled = partial(handle_users_reply, moltin_token_dataset=moltin_token_dataset)

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                print(entry["messaging"])
                sender_id = messaging_event["sender"]["id"]
                #db.set(sender_id, "START")

                if (sender_id == '5304713252982644') and not (messaging_event.get('delivery') or messaging_event.get('read')):
                    print(messaging_event)
                    if messaging_event.get("message"):
                        message_content = messaging_event["message"]["text"]
                    if messaging_event.get('postback'):
                        message_content = messaging_event['postback']['payload']
                    print(message_content)
                    handle_users_reply(sender_id, moltin_token_dataset, message_content)






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


def get_category_id_by_slug(category_slug, moltin_token_dataset):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    response = requests.get('https://api.moltin.com/v2/categories', headers=headers)
    response.raise_for_status()
    categories = response.json()['data']
    for category in categories:
        if category['slug'] == category_slug:
            return category['id']


def get_products_by_category_id(category_id, moltin_token_dataset):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get(f'https://api.moltin.com/v2/products?filter=eq(category.id,{category_id})',
                            headers=headers)
    response.raise_for_status()
    return response.json()


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
                "payload": "category::spicy"
            },
            {
                "type": "postback",
                "title": "Сытные",
                "payload": "category::nutritious"
            },
            {
                "type": "postback",
                "title": "Особые",
                "payload": "category::specials"
            }
        ]
    }



def get_serialized_product_dataset(product_dataset, moltin_token_dataset):

    product_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_img_url = get_file_url(moltin_token_dataset, product_img_id)
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

    params = {"access_token": FACEBOOK_TOKEN}
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

def get_menu_elements_set(catalogue, moltin_token_dataset):
    elements = []
    elements.append(get_main_menu())
    for product_dataset in catalogue:
        serialized_product_dataset = get_serialized_product_dataset(product_dataset, moltin_token_dataset)
        elements.append(serialized_product_dataset)
    elements.append(get_categories_menu())
    return elements

def send_gallery(recipient_id, catalogue, moltin_token_dataset):

    elements = []
    elements.append(get_main_menu())
    for product_dataset in catalogue:
        serialized_product_dataset = get_serialized_product_dataset(product_dataset, moltin_token_dataset)
        elements.append(serialized_product_dataset)
    elements.append(get_categories_menu())

    params = {"access_token": FACEBOOK_TOKEN}
    headers = {"Content-Type": "application/json"}

    request_content = {
          "recipient":{
            "id": recipient_id
          },
          "message":{
            "attachment":{
              "type":"template",
              "payload":{
                "template_type":"generic",
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


if __name__ == '__main__':
    app.run(debug=True)