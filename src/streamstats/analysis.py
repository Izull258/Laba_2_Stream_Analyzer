"""Потоковое накопление статистики по одному или нескольким файлам."""

import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from streamstats.errors import ConfigurationError, InvalidEventError, StreamStatsError
from streamstats.models import LEVELS, parse_event
from streamstats.parsers import iter_records

LOGGER = logging.getLogger(__name__)


def analyze_files(
    paths: Iterable[Path], file_format: str, skip_invalid: bool = False
) -> dict:
    """Вернуть общую статистику, сохраняя в памяти только счётчики."""
    file_paths = [Path(path) for path in paths]
    if not file_paths:
        raise ConfigurationError("не указан входной файл")

    levels = Counter({level: 0 for level in LEVELS})
    sources = Counter()
    error_sources = Counter()
    total = skipped = 0
    first: Optional[datetime] = None
    last: Optional[datetime] = None

    for path in file_paths:
        try:
            for line_number, raw_record, parse_error in iter_records(path, file_format):
                try:
                    if parse_error is not None:
                        raise parse_error
                    event = parse_event(raw_record)
                except InvalidEventError as error:
                    location = f"{path}:{line_number}: {error}"
                    if not skip_invalid:
                        raise type(error)(location) from error
                    LOGGER.warning("%s", location)
                    skipped += 1
                    continue

                total += 1
                levels[event.level] += 1
                sources[event.source] += 1
                if event.level in ("ERROR", "CRITICAL"):
                    error_sources[event.source] += 1
                moment = event.timestamp.astimezone(timezone.utc)
                if first is None or moment < first:
                    first = moment
                if last is None or moment > last:
                    last = moment
        except OSError as error:
            raise ConfigurationError(f"не удалось прочитать {path}: {error}") from error
        except UnicodeError as error:
            raise InvalidEventError(f"{path}: неверная кодировка UTF-8") from error
        except StreamStatsError as error:
            if str(error).startswith(str(path)):
                raise
            raise type(error)(f"{path}: {error}") from error

    top_five = sorted(error_sources.items(), key=lambda item: (-item[1], item[0]))[:5]
    return {
        "total_events": total,
        "skipped_invalid": skipped,
        "by_level": dict(levels),
        "by_source": dict(sorted(sources.items())),
        "top_error_sources": [
            {"source": source, "count": count} for source, count in top_five
        ],
        "first_timestamp": first.isoformat() if first else None,
        "last_timestamp": last.isoformat() if last else None,
    }
