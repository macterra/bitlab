from core.artifacts import ROOT, repo_path
import itertools
import unittest
from pathlib import Path

from core.lambda_calculus import CONS, FALSE, NIL, TRUE, app, bitlist, closed, read_bits
from examples.nought_rule30 import compile_program, step
from examples.rule30 import local_rule, step_function


def reference(row):
    # Lookup by Wolfram rule number, independently of the Boolean expression.
    padded = "0" + row + "0"
    return "".join(str((30 >> int(padded[i:i + 3], 2)) & 1) for i in range(len(row)))


class Rule30Tests(unittest.TestCase):
    def test_local_truth_table(self):
        for neighborhood, expected in zip(itertools.product("10", repeat=3), "00011110"):
            args = [TRUE if bit == "0" else FALSE for bit in neighborhood]
            result = read_bits(app(CONS, app(local_rule(), *args), NIL))
            self.assertEqual((result["status"], result["output"]), ("end", expected))

    def test_function_on_all_short_rows(self):
        term = step_function()
        self.assertTrue(closed(term))
        for width in range(6):
            for digits in itertools.product("01", repeat=width):
                row = "".join(digits)
                result = read_bits(app(term, bitlist(row)), budget=1000000, limit=width + 1)
                self.assertEqual((result["status"], result["output"]), ("end", reference(row)))

    def test_native_boundaries(self):
        for row in ("", "0", "1", "10", "01", "111", "000"):
            with self.subTest(row=row):
                self.assertEqual(step(row), reference(row))

    def test_native_trajectory(self):
        row = "0000001000000"
        for expected in ("0000011100000", "0000110010000", "0001101111000",
                         "0011001000100", "0110111101110"):
            self.assertEqual(expected, reference(row))
            row = step(row)
            self.assertEqual(row, expected)

    def test_artifact(self):
        source = repo_path("artifacts/nought/rule30.bits").read_text()
        self.assertEqual(source, compile_program())
        self.assertEqual(len(source), 1979)
        self.assertEqual(set(source), {"0", "1"})

    def test_invalid_input_and_incomplete_execution(self):
        with self.assertRaises(ValueError):
            step("012")
        with self.assertRaises(ValueError):
            step("1", budget=0)
        with self.assertRaises(RuntimeError):
            step("1", budget=1)


if __name__ == "__main__":
    unittest.main()
