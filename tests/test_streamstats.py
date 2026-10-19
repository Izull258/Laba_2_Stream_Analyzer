import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from streamstats.analysis import analyze_files
from streamstats.errors import (
    InvalidEventError,
    InvalidTimestampError,
    UnsupportedFormatError,
)
from streamstats.models import parse_event
from streamstats.parsers import iter_csv, iter_jsonl


def event(timestamp="2026-10-07T12:00:00+03:00", level="INFO", source="loader"):
    return {"timestamp": timestamp, "level": level, "source": source, "message": "Готово"}


class StreamStatsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def write(self, name, content):
        path = self.directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_jsonl_parser_yields_records_and_line_numbers(self):
        path = self.write("events.jsonl", json.dumps(event()) + "\nnot-json\n")
        rows = list(iter_jsonl(path))
        self.assertEqual([row[0] for row in rows], [1, 2])
        self.assertEqual(rows[0][1]["source"], "loader")
        self.assertIsInstance(rows[1][2], InvalidEventError)

    def test_csv_parser_reads_quoted_multiline_field(self):
        path = self.write(
            "events.csv",
            'timestamp,level,source,message\n'
            '2026-10-07T12:00:00+03:00,INFO,loader,"первая\nвторая"\n',
        )
        rows = list(iter_csv(path))
        self.assertEqual(rows[0][0], 3)
        self.assertEqual(rows[0][1]["message"], "первая\nвторая")

    def test_event_validation(self):
        self.assertEqual(parse_event(event()).source, "loader")
        with self.assertRaises(InvalidEventError):
            parse_event({**event(), "source": " "})
        with self.assertRaises(InvalidTimestampError):
            parse_event(event(timestamp="2026-10-07T12:00:00"))

    def test_empty_file(self):
        report = analyze_files([self.write("empty.jsonl", "")], "jsonl")
        self.assertEqual(report["total_events"], 0)
        self.assertIsNone(report["first_timestamp"])

    def test_multiple_files_and_timezone_order(self):
        first = self.write("first.jsonl", json.dumps(event(level="ERROR", source="Бета")) + "\n")
        second = self.write(
            "second.jsonl",
            json.dumps(event("2026-10-07T08:30:00+00:00", "CRITICAL", "Альфа"))
            + "\n"
            + json.dumps(event("2026-10-07T10:00:00+00:00", "INFO", "Бета"))
            + "\n",
        )
        report = analyze_files([first, second], "jsonl")
        self.assertEqual(report["total_events"], 3)
        self.assertEqual(report["by_level"]["ERROR"], 1)
        self.assertEqual(report["by_source"]["Бета"], 2)
        self.assertEqual(report["top_error_sources"], [
            {"source": "Альфа", "count": 1}, {"source": "Бета", "count": 1}
        ])
        self.assertEqual(report["first_timestamp"], "2026-10-07T08:30:00+00:00")
        self.assertEqual(report["last_timestamp"], "2026-10-07T10:00:00+00:00")

    def test_bad_jsonl_stops_with_location(self):
        path = self.write("bad.jsonl", json.dumps(event()) + "\n{broken\n")
        with self.assertRaisesRegex(InvalidEventError, "bad.jsonl:2"):
            analyze_files([path], "jsonl")

    def test_skip_bad_jsonl_and_continue(self):
        path = self.write("bad.jsonl", "{broken\n" + json.dumps(event()) + "\n")
        with self.assertLogs("streamstats.analysis", level="WARNING"):
            report = analyze_files([path], "jsonl", skip_invalid=True)
        self.assertEqual((report["total_events"], report["skipped_invalid"]), (1, 1))

    def test_skip_bad_csv_and_continue(self):
        path = self.write(
            "bad.csv",
            "timestamp,level,source,message\n"
            "2026-10-07T12:00:00+03:00,WRONG,loader,no\n"
            "2026-10-07T12:00:00+03:00,INFO,loader,ok\n",
        )
        with self.assertLogs("streamstats.analysis", level="WARNING"):
            report = analyze_files([path], "csv", skip_invalid=True)
        self.assertEqual((report["total_events"], report["skipped_invalid"]), (1, 1))

    def test_csv_surplus_column_is_invalid(self):
        path = self.write(
            "extra.csv",
            "timestamp,level,source,message\n"
            "2026-10-07T12:00:00+03:00,INFO,loader,ok,extra\n",
        )
        with self.assertRaisesRegex(InvalidEventError, "extra.csv:2"):
            analyze_files([path], "csv")

    def test_unsupported_format(self):
        with self.assertRaises(UnsupportedFormatError):
            analyze_files([self.directory / "x"], "xml")

    def test_cli_writes_report_and_reports_error(self):
        good = self.write("good.jsonl", json.dumps(event()) + "\n")
        output = self.directory / "report.json"
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        command = [sys.executable, "-m", "streamstats", "analyze", str(good), "--format", "jsonl"]
        success = subprocess.run(command + ["--output", str(output)], env=env, capture_output=True, text=True)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["total_events"], 1)
        failure = subprocess.run(command[:-1] + ["xml"], env=env, capture_output=True, text=True)
        self.assertEqual(failure.returncode, 2)
        self.assertIn("неподдерживаемый формат", failure.stderr)


if __name__ == "__main__":
    unittest.main()
