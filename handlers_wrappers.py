import logging
from fb_requests_handlers import send_message


def facebook_handler_wrapper():
    return


def moltin_changes_handler_wrapper():
    return


def cart_managment_wrapper(function, moltin_token_dataset, product_id, cart_id, sender_id):
    try:
        function(
            moltin_token_dataset=moltin_token_dataset,
            product_id=product_id,
            cart_id=cart_id
        )
        send_message(sender_id, 'Операция выполнена успешно')
    except Exception as err:
        logging.error('Ошибка операции с корзиной')
        logging.exception(err)
        send_message(
            sender_id,
            'Упс! Извините: случилась ошибка при выполнении')

