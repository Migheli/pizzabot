import json
from moltin_api_handlers import get_token_dataset, create_a_product, upload_img, set_main_image_to_product


adresses_url = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
menu_url = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'


with open('adresses.json', "r", encoding='utf-8') as adresses:
    serialized_adresses = json.load(adresses)


with open('menu.json', "r", encoding='utf-8') as menu:
    product_datasets = json.load(menu)


def main():
    moltin_token_dataset = get_token_dataset()

    for product_dataset in product_datasets:

        product_id = create_a_product(moltin_token_dataset, product_dataset)['data']['id']
        img_url = product_dataset['product_image']['url']
        img_id = upload_img(moltin_token_dataset, img_url)['data']['id']
        set_main_image_to_product(moltin_token_dataset, product_id, img_id)


if __name__ == '__main__':
    main()