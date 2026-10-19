"""Сериализация итогового отчёта."""

import json
from pathlib import Path

from streamstats.errors import ConfigurationError


def report_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def write_report(report: dict, path: Path) -> None:
    try:
        path.write_text(report_json(report), encoding="utf-8")
    except OSError as error:
        raise ConfigurationError(f"не удалось записать {path}: {error}") from error
