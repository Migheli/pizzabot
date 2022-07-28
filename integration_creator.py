from moltin_api_handlers import get_token_dataset, get_integration_webhook
import logging
import os

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    moltin_token_dataset = get_token_dataset()
    webhook_url = os.environ['NGROK_FORWARDING_URL']
    logger.info(get_integration_webhook(webhook_url, moltin_token_dataset)['data']['id'])


if __name__ == '__main__':
    main()
