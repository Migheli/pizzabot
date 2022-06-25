import requests
import os
from transliterate import translit
from textwrap import dedent


def get_token_dataset():

    data = {
        'client_id': os.getenv('MOLTIN_CLIENT_ID'),
        'client_secret': os.getenv('MOLTIN_CLIENT_SECRET'),
        'grant_type': 'client_credentials',
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()
    return response.json()


def get_product_catalogue(moltin_token_dataset):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_by_id(moltin_token, id):

    headers = {'Authorization': f'Bearer {moltin_token["access_token"]}'}
    response = requests.get(f'https://api.moltin.com/v2/products/{id}', headers=headers)
    response.raise_for_status()
    print('успешно сработал get_product_by_id')

    return response.json()


def add_product_to_cart(moltin_token_dataset, product_id, cart_id):
    print(product_id)
    print(cart_id)
    print(moltin_token_dataset["access_token"])

    get_product_by_id(moltin_token_dataset, product_id)
    get_cart_items(moltin_token_dataset, cart_id)

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    json_data = {
        'data': {
            'id': f'{product_id}',
            'type': 'cart_item',
            'quantity': int(1),
        },
    }
    response = requests.post(f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers, json=json_data)
    response.raise_for_status()


def get_cart_items(moltin_token_dataset, cart_id):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers)
    response.raise_for_status()
    print('успешно сработал get_cart_items')
    return response.json()


def delete_item_from_cart(moltin_token_dataset, cart_id, cart_item_id):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_id}/items/{cart_item_id}', headers=headers)
    response.raise_for_status()


def create_new_customer(moltin_token_dataset, first_name, last_name, email):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    json_data = {
        'data': {
            'type': 'customer',
            'name': f'{first_name} {last_name}',
            'email': f'{email}',
        },
    }
    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=json_data)
    response.raise_for_status()


def get_file_url(moltin_token_dataset, file_id):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']['link']['href']


def serialize_products_datasets(product_datasets):
    products = product_datasets['data']
    products_data_sets = []
    products_data_sets.append('в корзине сейчас:')
    for product in products:
        product_dataset = f"""\
        {product['name']}
        {product['description']}
        {product['unit_price']['amount']} {product['value']['currency']} за штуку
        В корзине {product['quantity']} шт. на общую сумму {product['value']['amount']}
        {product['value']['currency']}
        """
        products_data_sets.append(dedent(product_dataset))
    products_data_sets.append(
        f""" \nК оплате: {product_datasets['meta']['display_price']['with_tax']['amount']}""")
    serialized_datasets = ' '.join(products_data_sets)
    return serialized_datasets











def get_token_dataset():

    data = {
        'client_id': os.getenv('MOLTIN_CLIENT_ID'),
        'client_secret': os.getenv('MOLTIN_CLIENT_SECRET'),
        'grant_type': 'client_credentials',
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()
    return response.json()


entries_slug = 'pizza25'
def get_all_entries(moltin_token_dataset, flow_slug):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/entries?page[limit]=100', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def create_a_product(moltin_token_dataset, product_dataset):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    #print(str(product_dataset['name']))
    #print(translit(product_dataset['name'], language_code='ru', reversed=True).replace("'", "-").replace(" ", "-").lower())
    #print(str(product_dataset['id']))
    #print(str(product_dataset['description']))
    #print(int(product_dataset['price']))

    json_data = {
        'data':
        {
            'type': 'product',
            'name': str(product_dataset['name']),
            'slug': str(translit(product_dataset['name'], language_code='ru', reversed=True).replace("'", "-").replace(" ", "-").lower()),
            'sku': str(product_dataset['id']),
            'description': str(product_dataset['description']),
            'manage_stock': True,
            'price': [
                {
                    'amount': int(product_dataset['price']),
                    'currency': 'RUB',
                    'includes_tax': True,
                },
            ],
            'status': 'live',
            'commodity_type': 'physical',
        }}

    response = requests.post('https://api.moltin.com/v2/products', headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def upload_img(moltin_token_dataset, img_url):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    files = {
        'file_location': (None, img_url),
    }

    response = requests.post('https://api.moltin.com/v2/files',
                             headers=headers,
                             files=files)
    response.raise_for_status()
    return response.json()



def set_main_image_to_product(moltin_token_dataset, product_id, file_id):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    json_data = {
        'data': {
            'type': 'main_image',
            'id': file_id,
        },
    }

    response = requests.post(f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()


def get_entry_by_id(moltin_token_dataset, flow_slug, entry_id):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']

