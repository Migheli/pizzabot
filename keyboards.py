from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_product_keyboard(products_in_cart):
    print(products_in_cart)
    keyboard = [[InlineKeyboardButton
                 (text=f"Удалить из корзины: {product_in_cart['name']}",
                  callback_data=f"{product_in_cart['id']}")
                 ] for product_in_cart in products_in_cart
                ]
    keyboard.append([InlineKeyboardButton('В меню', callback_data='back')])
    keyboard.append([InlineKeyboardButton('Оплатить', callback_data='at_payment')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def get_products_datasets(products, max_products_per_page):
    for product in range(0, len(products), max_products_per_page):
        yield products[product:product + max_products_per_page]


def serialize_products_catalogue(products, max_products_per_page):
    products_datasets = list(get_products_datasets(products, max_products_per_page))
    return products_datasets


def get_multipage_keyboard(products_datasets, index_of_page):
    index_of_page = int(index_of_page)
    target_product_dataset = products_datasets[int(index_of_page)]
    keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in
                target_product_dataset]

    navigation_buttons = []

    if index_of_page > 0:
        back_products_button = InlineKeyboardButton('<<', callback_data=f"show_products_page::{index_of_page - 1}")
        navigation_buttons.append(back_products_button)

    if index_of_page + 1 < len(products_datasets):
        next_products_button = InlineKeyboardButton('>>', callback_data=f"show_products_page::{index_of_page + 1}")
        navigation_buttons.append(next_products_button)

    if navigation_buttons:
        keyboard.append(navigation_buttons)

    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])
    return keyboard


def get_delivery_type_keyboard(nearest_entry_id, longitude, latitude):
    return [
            [InlineKeyboardButton('Заберу сам', callback_data=f'self::{nearest_entry_id}::{longitude}::{latitude}')],
            [InlineKeyboardButton('Доставьте', callback_data=f'shpg::{nearest_entry_id}::{longitude}::{latitude}')]
            ]


def get_handle_menu_keyboard(product_id):

    return [[InlineKeyboardButton(text='Добавить в корзину', callback_data=f'{product_id}')],
            [InlineKeyboardButton('Назад', callback_data='back')],
            [InlineKeyboardButton('Корзина', callback_data='at_cart')]
            ]

