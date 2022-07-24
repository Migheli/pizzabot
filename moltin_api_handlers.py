import requests
import os
from textwrap import dedent


def create_and_get_cart_id(moltin_token_dataset, cart_name):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    json_data = {
        'data': {
        'name': f'{cart_name}',
        'description': 'cart',
        }
    }
    response = requests.post('https://api.moltin.com/v2/carts', json=json_data, headers=headers)
    response.raise_for_status()
    return response.json()['data']['id']

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

    return response.json()


def add_product_to_cart(moltin_token_dataset, product_id, cart_id):
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
    return response.json()


def delete_item_from_cart(moltin_token_dataset, cart_id, cart_item_id):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_id}/items/{cart_item_id}', headers=headers)
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


def get_all_entries(moltin_token_dataset, flow_slug):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/entries?page[limit]=100', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_entry_by_id(moltin_token_dataset, flow_slug, entry_id):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']
