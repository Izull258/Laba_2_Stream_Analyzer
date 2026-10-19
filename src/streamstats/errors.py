"""Ошибки анализа файлов событий."""


class StreamStatsError(Exception):
    """Базовая ошибка пакета."""


class UnsupportedFormatError(StreamStatsError):
    """Формат входного файла не поддерживается."""


class InvalidEventError(StreamStatsError):
    """Запись не соответствует модели события."""


class InvalidTimestampError(InvalidEventError):
    """Временная метка события неверна."""


class ConfigurationError(StreamStatsError):
    """Неверные аргументы CLI или недоступный файл."""
