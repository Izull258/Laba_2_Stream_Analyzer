"""Консольный интерфейс streamstats."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

from streamstats.analysis import analyze_files
from streamstats.errors import StreamStatsError
from streamstats.report import report_json, write_report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Потоковый анализ событий")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="создать статистический отчёт")
    analyze.add_argument("inputs", nargs="+", type=Path)
    analyze.add_argument("--format", required=True, dest="file_format")
    analyze.add_argument("--output", type=Path)
    analyze.add_argument("--skip-invalid", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        report = analyze_files(args.inputs, args.file_format, args.skip_invalid)
        if args.output is None:
            sys.stdout.write(report_json(report))
        else:
            write_report(report, args.output)
    except StreamStatsError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
