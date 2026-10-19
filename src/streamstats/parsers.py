"""Ленивое чтение записей из CSV и JSONL."""

import csv
import json
from pathlib import Path
from typing import Iterator, Optional, Tuple

from streamstats.errors import InvalidEventError, UnsupportedFormatError
from streamstats.models import FIELDS

# (номер физической строки, сырая запись, ошибка разбора)
RawRecord = Tuple[int, object, Optional[Exception]]


def iter_jsonl(path: Path) -> Iterator[RawRecord]:
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                yield line_number, None, InvalidEventError(f"неверный JSON: {error.msg}")
            else:
                yield line_number, record, None


def iter_csv(path: Path) -> Iterator[RawRecord]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        try:
            fields = reader.fieldnames
        except csv.Error as error:
            raise InvalidEventError(f"неверный заголовок CSV: {error}") from error
        if fields is None:
            return
        missing = set(FIELDS) - set(fields)
        if missing:
            raise InvalidEventError(
                "в заголовке CSV нет полей: " + ", ".join(sorted(missing))
            )
        while True:
            try:
                record = next(reader)
            except StopIteration:
                return
            except csv.Error as error:
                yield reader.line_num, None, InvalidEventError(f"неверная строка CSV: {error}")
            else:
                if None in record:
                    yield reader.line_num, None, InvalidEventError(
                        "число полей CSV больше числа столбцов"
                    )
                else:
                    yield reader.line_num, record, None


def iter_records(path: Path, file_format: str) -> Iterator[RawRecord]:
    if file_format == "jsonl":
        return iter_jsonl(path)
    if file_format == "csv":
        return iter_csv(path)
    raise UnsupportedFormatError(f"неподдерживаемый формат: {file_format}")
