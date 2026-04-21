import abc
from datetime import datetime, timezone
from typing import Any, Dict

import psycopg
from psycopg.rows import dict_row

from postgres_to_es.utils.backoff import backoff


class BaseStorage(abc.ABC):
    """Абстрактное хранилище состояния."""

    @abc.abstractmethod
    def save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в хранилище."""

    @abc.abstractmethod
    def retrieve_state(self) -> Dict[str, Any]:
        """Получить состояние из хранилища."""


class PostgresStateStorage(BaseStorage):
    """Хранилище состояния в Postgres."""

    def __init__(self, conn, key: str = "last_modified"):
        self.conn = conn
        self.key = key

    @backoff()
    def save_state(self, state: datetime):
        """Сохранить состояние в хранилище."""
        query = ("INSERT INTO etl_state (key, value)"
                 " VALUES (%s, %s) "
                 "ON CONFLICT (key) "
                 "DO UPDATE "
                 "SET value = EXCLUDED.value;")

        with self.conn.cursor() as cursor:
            cursor.execute(query, (self.key, state))

        self.conn.commit()

    @backoff()
    def retrieve_state(self) -> datetime:
        """Получить состояние из хранилища."""
        query = "SELECT value FROM etl_state WHERE key = %s;"

        with self.conn.cursor() as cursor:
            cursor.execute(query, (self.key,))
            row = cursor.fetchone()

            if not row:
                return datetime(1970, 1, 1, tzinfo=timezone.utc)

            return row[0]
