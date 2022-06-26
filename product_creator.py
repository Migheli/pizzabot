import json
import os
import requests
from transliterate import translit
from moltin_api_handlers import get_token_dataset


addresses_file_path = os.getenv('ADRESSES_FILE_PATH')
menu_file_path = os.getenv('MENU_FILE_PATH')

with open(f'{addresses_file_path}', "r", encoding='utf-8') as addresses:
    serialized_adresses = json.load(addresses)

with open(f'{menu_file_path}', "r", encoding='utf-8') as menu:
    product_datasets = json.load(menu)


def create_a_product(moltin_token_dataset, product_dataset):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    json_data = {
        'data':
        {
            'type': 'product',
            'name': product_dataset['name'],
            'slug': translit(product_dataset['name'], language_code='ru', reversed=True).replace("'", "-").replace(" ", "-").lower(),
            'sku': product_dataset['id'],
            'description': product_dataset['description'],
            'manage_stock': False,
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


def main():
    moltin_token_dataset = get_token_dataset()

    for product_dataset in product_datasets:

        product_id = create_a_product(moltin_token_dataset, product_dataset)['data']['id']
        img_url = product_dataset['product_image']['url']
        img_id = upload_img(moltin_token_dataset, img_url)['data']['id']
        set_main_image_to_product(moltin_token_dataset, product_id, img_id)


if __name__ == '__main__':
    main()
