import json
import requests
from moltin_api_handlers import get_token_dataset, create_a_product, upload_img, set_main_image_to_product


def create_new_flow(moltin_token_dataset, flow_name):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    json_data = {
        'data': {
            'type': 'flow',
            'name': str(flow_name),
            'slug': str(flow_name.lower()),
            'description': str(f'{flow_name}_flow'),
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
            'name': str(field_name),
            'slug': str(field_name.lower()),
            'field_type': str(field_type),
            'description': f'{field_name}_field',
            'required': False,
            'default': 0,
            'enabled': True,
            'order': int(1),
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': str(flow_id),
                    },
                },
            },
        },
    }
    response = requests.post('https://api.moltin.com/v2/fields', headers=headers, json=json_data)
    response.raise_for_status()
    print(response.json())
    return response.json()


# здесь потребуется OrderedDict для версий Python < 3.6
field_data = {
        #'Address': 'string',
        #'Alias': 'string',
        #'Longitude': 'float',
        #'Latitude': 'float',
        'Deliveryman_tg_id': 'string',
    }


def create_new_customer(moltin_token_dataset, flow_slug, longitude, latitude):
    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}
    json_data = {
        'data': {
            'type': 'entry',
            'longitude': float(longitude),
            'latitude': float(latitude),
                }}
    response = requests.post(f'https://api.moltin.com/v2/flows/{str(flow_slug)}/entries', headers=headers,
                             json=json_data)
    print(response.status_code)
    response.raise_for_status()
    return response.json()['data']


def create_new_entry(moltin_token_dataset, flow_slug, field_slug_dataset, address, alias, longitude, latitude):
    address_slug, alias_slug, longitude_slug, latitude_slug = field_slug_dataset

    headers = {'Authorization': f'Bearer {moltin_token_dataset["access_token"]}'}

    #print(str(address_slug))
    #print(str(str(address)))
    json_data = {
        'data': {
            'type': 'entry',
            address_slug: address,
            alias_slug: alias,
            longitude_slug: longitude,
            latitude_slug: latitude,
            'Deliveryman_tg_id': '228686255',
    }}
    response = requests.post(f'https://api.moltin.com/v2/flows/{str(flow_slug)}/entries', headers=headers, json=json_data)
    response.raise_for_status()


def main():
    moltin_token_dataset = get_token_dataset()
    flow_name = 'Customer_Address'
    flow = create_new_flow(moltin_token_dataset, flow_name)
    flow_id = flow['data']['id']
    flow_slug = flow['data']['slug']
    field_slug_dataset = []
    for field_name, field_type in field_data.items():
        field = create_new_flow_field(moltin_token_dataset, flow_id, field_name, field_type)
        field_slug_dataset.append(field['data']['slug'])

    flow_name = 'pizza25'
    flow = create_new_flow(moltin_token_dataset, flow_name)
    flow_id = flow['data']['id']
    flow_slug = flow['data']['slug']
    field_slug_dataset = []
    for field_name, field_type in field_data.items():
        print(field_name)
        print(field_type)
        field = create_new_flow_field(moltin_token_dataset, flow_id, field_name, field_type)
        field_slug_dataset.append(field['data']['slug'])

    with open('adresses.json', "r", encoding='utf-8') as adresses:
        serialized_adresses = json.load(adresses)

    for serialized_adress in serialized_adresses:
        print(serialized_adress)
        address = serialized_adress['address']['full']
        alias = serialized_adress['alias']
        longitude = serialized_adress['coordinates']['lon']
        latitude = serialized_adress['coordinates']['lat']

        create_new_entry(moltin_token_dataset, flow_slug, field_slug_dataset, address, alias, longitude, latitude)


if __name__ == '__main__':
    main()