import requests
import os
from textwrap import dedent
import time


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


def check_token_status(moltin_token_dataset):
    """
    Проверяет актуальность токена по времени его действия и, в случае необходимости, обновляет его.
    """
    if int(time.time()) >= moltin_token_dataset['expires']:
        moltin_token_dataset = get_token_dataset()
    return moltin_token_dataset


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
    print(response.json())


def get_cart_by_reference(moltin_token_dataset, cart_id):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}', headers=headers)
    response.raise_for_status()
    return response.json()


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


def get_category_id_by_slug(category_slug, moltin_token_dataset):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.get('https://api.moltin.com/v2/categories', headers=headers)
    response.raise_for_status()
    categories = response.json()['data']
    for category in categories:
        if category['slug'] == category_slug:
            return category['id']


def get_integration_webhook(webhook_url, moltin_token_dataset):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    json_data = {
        'data': {
            'type': 'integration',
            'name': 'Changes menu notificator',
            'description': 'Sends a post request to the webhook in case of menu changes',
            'enabled': True,
            'observes': [
                'product.created',
                'product.updated',
                'product.deleted',
            ],
            'integration_type': 'webhook',
            'configuration': {
                'url': f'{webhook_url}/changes_checker',
            },
        },
    }

    response = requests.post('https://api.moltin.com/v2/integrations', headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def delete_integration_webhook(moltin_token_dataset, integration_id):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    response = requests.delete(f'https://api.moltin.com/v2/integrations/{integration_id}', headers=headers)
    response.raise_for_status()
    return response.json()


