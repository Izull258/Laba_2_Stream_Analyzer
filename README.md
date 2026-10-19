# Лабораторная 2: streamstats

Потоковый анализатор событий из CSV и JSONL. Требуется Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[test]'
python -m streamstats analyze events.jsonl --format jsonl --output report.json
python -m streamstats analyze events1.csv events2.csv --format csv --skip-invalid
python -m pytest
ruff check .
```

Если `--output` не указан, JSON выводится в stdout. Ошибки и предупреждения
выводятся в stderr. При ошибке команда завершается с кодом 2.

Каждое событие содержит `timestamp`, `level`, `source`, `message`.
`timestamp` — дата и время ISO 8601 с часовым поясом; отчёт приводит
первую и последнюю метки к UTC. `level` — один из DEBUG, INFO, WARNING,
ERROR, CRITICAL; `source` — непустая строка, `message` — строка.
Дополнительные поля не учитываются.

Поля отчёта: `total_events`, `skipped_invalid`, `by_level`, `by_source`,
`top_error_sources`, `first_timestamp`, `last_timestamp`. Список top-5
сортируется по убыванию числа ERROR/CRITICAL, при равенстве — по имени
источника. Для пустого файла временные метки равны `null`.

Файлы читаются по одной записи; в памяти остаются текущая запись и счётчики.
CSV-запись может занимать несколько физических строк; для ошибки указывается
номер строки, на которой закончилась запись. Неверный заголовок CSV нельзя
исправить пропуском строк, поэтому он всегда останавливает обработку.
