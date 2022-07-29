import os
from moltin_api_handlers import get_file_url, get_product_catalogue
import json

categories_id = {
        'basic': os.environ['BASIC_CATEGORY_ID'],
        'spicy': os.environ['SPICY_CATEGORY_ID'],
        'nutritious': os.environ['NUTRITIOUS_CATEGORY_ID'],
        'specials': os.environ['SPECIALS_CATEGORY_ID'],
    }


def set_main_img_href(product_dataset, moltin_token_dataset):
    product_img_id =\
        product_dataset['relationships']['main_image']['data']['id']
    product_dataset['relationships']['main_image']['data']['href']\
        = get_file_url(moltin_token_dataset, product_img_id)


def update_database(db, moltin_token_dataset):
    menu = get_product_catalogue(moltin_token_dataset)
    for product_dataset in menu['data']:
        set_main_img_href(product_dataset, moltin_token_dataset)
    menu = json.dumps(menu)
    db.set('menu', menu)


def get_categorised_products_set(cached_menu):
    return filter(
        lambda product: product['relationships'].get('categories'),
        cached_menu
    )


def get_cached_products_by_category_id(
        categorised_products_set,
        target_category_id):
    return [
        product for product in categorised_products_set
        if product['relationships']['categories']['data'][0]['id']
           == target_category_id
    ]
