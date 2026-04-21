from elasticsearch import Elasticsearch

from postgres_to_es.utils.backoff import backoff
from postgres_to_es.utils.logger import get_logger

logger = get_logger(__name__)


class ElasticsearchInitializer:
    """Инициализация Elasticsearch."""
    def __init__(self, host: str):
        self.es = Elasticsearch(host)

    @backoff()
    def create_index_if_not_exists(self, index_name: str, mapping: dict):
        """Создание индекса."""
        if self.es.indices.exists(index=index_name):
            logger.info("Index %s already exists", index_name)
            return

        logger.info("Creating index %s", index_name)

        self.es.indices.create(
            index=index_name,
            body=mapping
        )

        logger.info("Index %s created", index_name)
