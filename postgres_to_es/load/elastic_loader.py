from elasticsearch import Elasticsearch, helpers

from postgres_to_es.utils.backoff import backoff
from postgres_to_es.utils.logger import get_logger

logger = get_logger(__name__)


class ElasticLoader:
    """Загрузчик данных в Elasticsearch."""

    def __init__(self, host: str, index: str = "movies"):
        self.client = Elasticsearch(hosts=[host])
        self.index = index

    def _generate_actions(self, docs):
        for doc in docs:
            yield {
                "_index": self.index,
                "_id": doc["id"],
                "_source": doc,
            }

    @backoff()
    def bulk_load(self, docs: list[dict]):
        """Загрузка данных в Elasticsearch."""
        logger.info("Sending %s documents to Elasticsearch", len(docs))
        if not docs:
            return

        success, failed = helpers.bulk(
            self.client,
            self._generate_actions(docs),
            raise_on_error=False,
            stats_only=False
        )

        if failed:
            logger.error("Bulk insert failed: %s", failed)
            raise Exception(f"Bulk load failed: {failed} documents")

        logger.info("Successfully indexed %s documents", success)
        return success
