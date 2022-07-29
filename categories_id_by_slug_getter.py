from moltin_api_handlers import get_token_dataset, get_category_id_by_slug
import logging

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    moltin_token_dataset = get_token_dataset()
    category_slug = input(
        'Введите slug для категории, ID которой хотите получить'
    )
    logger.info(get_category_id_by_slug(category_slug, moltin_token_dataset))


if __name__ == '__main__':
    main()
