import time
from datetime import timedelta, timezone

import psycopg

from postgres_to_es.config import PG_DSN, ES_HOST, MOVIES_INDEX, MOVIES_MAPPING
from postgres_to_es.extract.postgres_extractor import PostgresExtractor
from postgres_to_es.init.es_init import ElasticsearchInitializer
from postgres_to_es.load.elastic_loader import ElasticLoader
from postgres_to_es.state.storage import PostgresStateStorage
from postgres_to_es.transform.transformer import Transformer
from postgres_to_es.utils.logger import get_logger

logger = get_logger(__name__)


def init_state_table(conn):
    """Создание таблицы хранения состояния."""
    query = """
            CREATE TABLE IF NOT EXISTS etl_state
            (
                key
                TEXT
                PRIMARY
                KEY,
                value
                TIMESTAMPTZ
            ); \
            """
    with conn.cursor() as cursor:
        cursor.execute(query)
    conn.commit()


def to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def main():
    conn = psycopg.connect(PG_DSN)
    init_state_table(conn)

    es_init = ElasticsearchInitializer(ES_HOST)
    es_init.create_index_if_not_exists(
        MOVIES_INDEX,
        MOVIES_MAPPING
    )

    state_storage = PostgresStateStorage(conn)
    extractor = PostgresExtractor(conn)
    transformer = Transformer()
    loader = ElasticLoader(ES_HOST)

    logger.info("ETL started")
    while True:
        last_state = state_storage.retrieve_state()

        new_state = last_state
        has_data = False

        for batch in extractor.extract(last_state):
            has_data = True

            docs = transformer.transform(batch)
            loader.bulk_load(docs)

            for row in batch:
                fw_modified = to_utc(row.get("modified"))
                if fw_modified and fw_modified > new_state:
                    new_state = fw_modified

        if has_data:
            state_storage.save_state(new_state + timedelta(seconds=1))

        time.sleep(5)


if __name__ == "__main__":
    main()
