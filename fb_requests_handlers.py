import os
import json
import requests


def send_message(recipient_id, message_text):
    params = {"access_token": os.environ["FB_PAGE_ACCESS_TOKEN"]}
    headers = {"Content-Type": "application/json"}
    request_content = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params,
        headers=headers,
        data=request_content
    )
    response.raise_for_status()


def get_cart_page(cart_price):
    return \
        {
            "title": "Корзина",
            "image_url": os.environ["CART_LOGO_URL"],
            "subtitle": f"Ваш заказ на сумму {cart_price}",
            "default_action":
                {
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
        serialized_product_dataset = \
            {
                "title": f"{cart_item['name']}. В корзине: {cart_item['quantity']} шт.",
                "image_url": cart_item['image']['href'],
                "subtitle": f"{cart_item['description']}",
                "default_action": {
                    "type": "web_url",
                    "url": "https://www.originalcoastclothing.com/",
                    "webview_height_ratio": "compact",
                },
                "buttons": [
                    {
                        "type": "postback",
                        "title": "Добавить еще одну",
                        "payload": f"in_cart_menu::add::{cart_item['product_id']}"
                    },

                    {
                        "type": "postback",
                        "title": "Удалить из корзины",
                        "payload": f"in_cart_menu::replace::{cart_item['id']}"
                    },
                ]
            }
        elements.append(serialized_product_dataset)
    return elements


def send_gallery(recipient_id, elements):

    params = {"access_token": os.environ["FB_PAGE_ACCESS_TOKEN"]}
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
    elements.append(
        {
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
    )
    for product_dataset in catalogue:
        serialized_product_dataset = \
            {
                "title": f"{product_dataset['name']} ({product_dataset['price'][0]['amount']} руб.)",
                "image_url": product_dataset['relationships']['main_image']['data']['href'],
                "subtitle": product_dataset['description'],
                "default_action": {
                    "type": "web_url",
                    "url": product_dataset['relationships']['main_image']['data']['href'],
                    "webview_height_ratio": "compact",
                },
                "buttons": [
                              {
                                "type": "postback",
                                "title": "В корзину",
                                "payload": f"in_menu::add::{product_dataset['id']}"
                              }
                ]
            }

        elements.append(serialized_product_dataset)
    elements.append(
        {
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
                "payload": "in_menu::send_category_menu::spicy"
            },
            {
                "type": "postback",
                "title": "Сытные",
                "payload": "in_menu::send_category_menu::nutritious"
            },
            {
                "type": "postback",
                "title": "Особые",
                "payload": "in_menu::send_category_menu::specials"
            }
        ]
    }
    )
    return elements
