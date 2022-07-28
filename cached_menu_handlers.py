import os

categories_id = {
        'basic': os.environ['BASIC_CATEGORY_ID'],
        'spicy': os.environ['SPICY_CATEGORY_ID'],
        'nutritious': os.environ['NUTRITIOUS_CATEGORY_ID'],
        'specials': os.environ['SPECIALS_CATEGORY_ID'],
    }

def get_categorised_products_set(cached_menu):
    return filter(lambda product: product['relationships'].get('categories'), cached_menu)

def get_cached_products_by_category_id(categorised_products_set, target_category_id):
    return [product for product in categorised_products_set if product['relationships']['categories']['data'][0]['id'] == target_category_id]

