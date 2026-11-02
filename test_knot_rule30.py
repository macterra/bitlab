import itertools
import json
import unittest
from pathlib import Path

from functional import app, bitlist, closed, read_bits
from knot_rule30 import encode_input, history_function, metrics, program, run
from total_bcl import build


def reference(row, count):
    rows = [row]
    for _ in range(count):
        padded = "0" + row + "0"
        row = "".join(str((30 >> int(padded[i:i + 3], 2)) & 1) for i in range(len(row)))
        rows.append(row)
    return "".join(rows)


class KnotRule30Tests(unittest.TestCase):
    def test_lambda_history_on_short_rows(self):
        term = history_function()
        self.assertTrue(closed(term))
        for width in range(4):
            for digits in itertools.product("01", repeat=width):
                row = "".join(digits)
                for count in range(4):
                    expected = reference(row, count)
                    result = read_bits(app(term, bitlist(encode_input(row, count))),
                                       budget=1000000, limit=len(expected) + 1)
                    self.assertEqual((result["status"], result["output"]), ("end", expected))

    def test_five_generations_in_one_native_invocation(self):
        # Run the saved native source directly on the ordinary raw input interface.
        # No Python generation loop or calls to the single-generation guest.
        source = Path(__file__).with_name("knot_rule30.bits").read_text()
        row = "0000001000000"
        result = read_bits(app(build()[1], bitlist(source), bitlist("111110" + row)),
                           budget=100000000, limit=79)
        self.assertEqual((result["status"], result["output"]), ("end", reference(row, 5)))

    def test_zero_generations_and_empty_rows(self):
        for row, count in (("101", 0), ("", 0), ("", 4), ("1", 3)):
            with self.subTest(row=row, count=count):
                self.assertEqual(run(row, count)["output"], reference(row, count))

    def test_output_longer_than_default_observer_limit(self):
        row = "01" * 26
        self.assertEqual(run(row, 1)["output"], reference(row, 1))

    def test_missing_count_delimiter(self):
        for bits in ("", "1", "111"):
            result = read_bits(app(build()[1], bitlist(program()), bitlist(bits)), budget=1000000)
            self.assertEqual((result["status"], result["output"]), ("end", ""))

    def test_invalid_arguments_and_incomplete_execution(self):
        for row, count in (("012", 1), ("0", -1), ("0", 1.5)):
            with self.assertRaises(ValueError):
                encode_input(row, count)
        with self.assertRaises(ValueError):
            run("0", budget=0)
        with self.assertRaises(RuntimeError):
            run("0", budget=1)

    def test_artifacts(self):
        root = Path(__file__).parent
        self.assertEqual((root / "knot_rule30.bits").read_text(), program())
        self.assertEqual(json.loads((root / "knot_rule30_metrics.json").read_text()), metrics())


if __name__ == "__main__":
    unittest.main()
