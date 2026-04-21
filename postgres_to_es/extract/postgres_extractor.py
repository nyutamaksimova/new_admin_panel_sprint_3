from datetime import datetime

from psycopg.rows import dict_row

from postgres_to_es.utils.logger import get_logger

logger = get_logger(__name__)


class PostgresExtractor:
    """Получение данных из Postgres"""

    def __init__(self, conn, batch_size: int = 100):
        self.conn = conn
        self.batch_size = batch_size

    def split_to_batches(self, items, size):
        for i in range(0, len(items), size):
            yield items[i:i + size]

    def get_changed_film_ids(self, last_modified: datetime):
        """Получение id фильмов с измененными данными."""
        logger.info("Fetching changed film ids since %s", last_modified)
        query = """
                WITH changed_fw AS (SELECT id
                                    FROM content.film_work
                                    WHERE modified > %(last_modified)s

                                    UNION

                                    SELECT gfw.film_work_id
                                    FROM content.genre g
                                             JOIN content.genre_film_work gfw ON g.id = gfw.genre_id
                                    WHERE g.modified > %(last_modified)s

                                    UNION

                                    SELECT film_work_id
                                    FROM content.genre_film_work
                                    WHERE created > %(last_modified)s

                                    UNION

                                    SELECT pfw.film_work_id
                                    FROM content.person p
                                             JOIN content.person_film_work pfw ON p.id = pfw.person_id
                                    WHERE p.modified > %(last_modified)s

                                    UNION

                                    SELECT film_work_id
                                    FROM content.person_film_work
                                    WHERE created > %(last_modified)s)

                SELECT DISTINCT id
                FROM changed_fw
                ORDER BY id; \
                """

        with self.conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, {"last_modified": last_modified})
            rows = cursor.fetchall()
        logger.info("Found %s changed films", len(rows))
        return [row["id"] for row in rows]

    def get_full_data(self, film_ids):
        """Полная выгрузка измененных данных."""

        query = """
                SELECT fw.id,
                       fw.title,
                       fw.description,
                       fw.rating,
                       fw.modified,

                       COALESCE(
                               ARRAY_AGG(DISTINCT g.name)
                               FILTER(WHERE g.name IS NOT NULL),
                               '{}'
                       ) AS genres,

                       COALESCE(
                               JSON_AGG(
                                   DISTINCT jsonb_build_object(
                        'id', p.id,
                        'name', p.full_name,
                        'role', pfw.role
                    )
                ) FILTER(WHERE p.id IS NOT NULL),
                               '[]'
                       ) AS persons

                FROM content.film_work fw
                         LEFT JOIN content.genre_film_work gfw ON fw.id = gfw.film_work_id
                         LEFT JOIN content.genre g ON g.id = gfw.genre_id
                         LEFT JOIN content.person_film_work pfw ON fw.id = pfw.film_work_id
                         LEFT JOIN content.person p ON p.id = pfw.person_id

                WHERE fw.id = ANY (%s)

                GROUP BY fw.id; \
                """

        with self.conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (film_ids,))
            return cursor.fetchall()

    def extract(self, last_modified: datetime):
        """Выгрузка и разделение на батчи."""

        film_ids = self.get_changed_film_ids(last_modified)

        if not film_ids:
            return

        for batch_ids in self.split_to_batches(film_ids, self.batch_size):
            rows = self.get_full_data(batch_ids)

            if rows:
                yield rows
