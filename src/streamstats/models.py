"""Модель и проверка одного события."""

from dataclasses import dataclass
from datetime import datetime

from streamstats.errors import InvalidEventError, InvalidTimestampError

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
FIELDS = ("timestamp", "level", "source", "message")


@dataclass(frozen=True)
class Event:
    timestamp: datetime
    level: str
    source: str
    message: str


def parse_event(record: object) -> Event:
    if not isinstance(record, dict):
        raise InvalidEventError("событие должно быть объектом")

    for field in FIELDS:
        if field not in record:
            raise InvalidEventError(f"отсутствует поле {field}")
        if not isinstance(record[field], str):
            raise InvalidEventError(f"поле {field} должно быть строкой")

    if record["level"] not in LEVELS:
        raise InvalidEventError("неизвестный уровень события")
    if not record["source"].strip():
        raise InvalidEventError("источник не может быть пустым")

    stamp = record["timestamp"]
    if "T" not in stamp and " " not in stamp:
        raise InvalidTimestampError("нужны дата и время ISO 8601")
    try:
        timestamp = datetime.fromisoformat(stamp)
    except ValueError as error:
        raise InvalidTimestampError("неверная временная метка ISO 8601") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise InvalidTimestampError("временная метка должна содержать часовой пояс")

    return Event(timestamp, record["level"], record["source"], record["message"])
