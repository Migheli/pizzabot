import json
import requests
import os
from moltin_api_handlers import get_token_dataset


def create_new_flow(moltin_token_dataset, flow_name):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    json_data = {
        'data': {
            'type': 'flow',
            'name': flow_name,
            'slug': flow_name.lower(),
            'description': f'{flow_name}_flow',
            'enabled': True,
        },
    }
    response = requests.post('https://api.moltin.com/v2/flows', headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def create_new_flow_field(moltin_token_dataset, flow_id, field_name, field_type):

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    json_data = {
        'data': {
            'type': 'field',
            'name': field_name,
            'slug': field_name.lower(),
            'field_type': field_type,
            'description': f'{field_name}_field',
            'required': False,
            'default': 0,
            'enabled': True,
            'order': 1,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    },
                },
            },
        },
    }
    response = requests.post('https://api.moltin.com/v2/fields', headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


field_data = {
    'Address': 'string',
    'Alias': 'string',
    'Longitude': 'float',
    'Latitude': 'float',
    'Deliveryman_tg_id': 'string',
}


def create_new_customer(moltin_token_dataset, flow_slug, longitude, latitude):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    json_data = {
        'data': {
            'type': 'entry',
            'longitude': longitude,
            'latitude': latitude,
        }
    }
    response = requests.post(f'https://api.moltin.com/v2/flows/{flow_slug}/entries', headers=headers,
                             json=json_data)
    response.raise_for_status()
    return response.json()['data']


def create_new_entry(moltin_token_dataset, flow_slug, field_slug_dataset, address, alias, longitude, latitude):
    address_slug, alias_slug, longitude_slug, latitude_slug = field_slug_dataset

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    json_data = {
        'data': {
            'type': 'entry',
            address_slug: address,
            alias_slug: alias,
            longitude_slug: longitude,
            latitude_slug: latitude,
            'Deliveryman_tg_id': os.getenv('DELIVERYMAN_TG_ID'),
        }
    }

    response = requests.post(f'https://api.moltin.com/v2/flows/{flow_slug}/entries',
                             headers=headers, json=json_data)
    response.raise_for_status()


def main():
    addresses_file_path = os.getenv('ADRESSES_FILE_PATH')
    moltin_token_dataset = get_token_dataset()
    flow_name = os.getenv('FLOW_TO_CREATE_NAME')
    flow = create_new_flow(moltin_token_dataset, flow_name)
    flow_id = flow['data']['id']
    flow_slug = flow['data']['slug']
    field_slug_dataset = []
    for field_name, field_type in field_data.items():
        field = create_new_flow_field(moltin_token_dataset, flow_id, field_name, field_type)
        field_slug_dataset.append(field['data']['slug'])

    with open(addresses_file_path, "r", encoding='utf-8') as adresses:
        serialized_addresses = json.load(adresses)

    for serialized_address in serialized_addresses:
        address = serialized_address['address']['full']
        alias = serialized_address['alias']
        longitude = serialized_address['coordinates']['lon']
        latitude = serialized_address['coordinates']['lat']

        create_new_entry(moltin_token_dataset, flow_slug, field_slug_dataset, address, alias, longitude, latitude)


if __name__ == '__main__':
    main()
