from postgres_to_es.utils.logger import get_logger

logger = get_logger(__name__)


class Transformer:
    """Обработка данных из Postgres в Elasticsearch."""

    def transform(self, rows: list[dict]) -> list[dict]:
        logger.info("Transforming %s rows", len(rows))
        return [self._transform_row(row) for row in rows]

    def _transform_row(self, row: dict) -> dict:
        """Преобразование данных."""
        persons = row.get("persons") or []

        actors = []
        writers = []
        directors = []

        actors_names = set()
        writers_names = set()
        directors_names = set()

        for person in persons:
            role = (person.get("role") or "").lower()

            person_data = {
                "id": str(person.get("id")),
                "name": person.get("name") or "",
            }

            if role == "actor":
                actors.append(person_data)
                actors_names.add(person_data["name"])

            elif role == "writer":
                writers.append(person_data)
                writers_names.add(person_data["name"])

            elif role == "director":
                directors.append(person_data)
                directors_names.add(person_data["name"])

        return {
            "id": str(row["id"]),
            "title": row.get("title") or "",
            "description": row.get("description") or "",
            "imdb_rating": float(row["rating"] or 0.0),
            "genres": row.get("genres") or [],
            "actors": actors,
            "writers": writers,
            "directors": directors,
            "actors_names": list(actors_names),
            "writers_names": list(writers_names),
            "directors_names": list(directors_names),
        }
