import argparse
import logging
from moltin_api_handlers import get_token_dataset, get_category_id_by_slug


logger = logging.getLogger(__name__)

def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('slug', type=str, help='Input slug for product category')
    args = parser.parse_args()
    moltin_token_dataset = get_token_dataset()
    logger.info(get_category_id_by_slug(args.slug, moltin_token_dataset))


if __name__ == '__main__':
    main()
