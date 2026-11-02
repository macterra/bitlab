from core.artifacts import ROOT, repo_path
import itertools
import json
import unittest
from pathlib import Path

from core.combinators import sk_lambda
from core.lambda_calculus import IDENTITY, Machine, app, bitlist, closed, encode, normalize, read_bits
from core.rewrites import replay
from core.reflection import reflection_seed
from examples.rule30 import step_function
from languages.knot import build, compile_program, native_encode, report, seed


def reference_parse(bits):
    """Independent tree parser with explicit completion and a returned suffix."""
    position = 0

    def parse():
        nonlocal position
        if position == len(bits):
            return "K"
        first = bits[position]
        position += 1
        if first == "1":
            return app(parse(), parse())
        if position == len(bits):
            return "K"
        second = bits[position]
        position += 1
        return "K" if second == "0" else "S"

    tree = parse()
    return tree, bits[position:]


class TotalBCLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.reflected, cls.metrics = build()

    def test_rewrite_certificates(self):
        self.assertEqual(replay(seed(), self.metrics["proof"]), self.base)
        self.assertEqual(replay(reflection_seed(self.base), self.metrics["reflection_proof"]), self.reflected)
        self.assertTrue(closed(self.base))
        self.assertTrue(closed(self.reflected))

    def test_all_short_strings(self):
        for width in range(8):
            for digits in itertools.product("01", repeat=width):
                source = "".join(digits)
                tree, _ = reference_parse(source)
                expected = normalize(sk_lambda(tree))
                self.assertEqual(normalize(app(self.base, bitlist(source))), expected)
                if source:
                    self.assertEqual(normalize(app(self.reflected, bitlist(source))), expected)
                self.assertTrue(closed(app(self.reflected, bitlist(source))))
                self.assertIn(Machine(app(self.reflected, bitlist(source))).run(10000), ("value", "suspended"))

    def test_compact_codes_and_unused_suffixes(self):
        for tree in ("K", "S", app("S", "K", "K"), app("K", "S")):
            source = native_encode(tree)
            self.assertEqual(reference_parse(source), (tree, ""))
            for suffix in ("", "0", "1", "10101"):
                self.assertEqual(reference_parse(source + suffix), (tree, suffix))
                self.assertEqual(normalize(app(self.reflected, bitlist(source + suffix))),
                                 normalize(sk_lambda(tree)))
        self.assertEqual(native_encode("K"), "00")
        self.assertEqual(native_encode("S"), "01")

    def test_ordinary_native_self_interpreter(self):
        guest = compile_program(IDENTITY)
        result = read_bits(app(self.base, bitlist(self.metrics["ordinary_self_program"]),
                               bitlist(guest), bitlist("101")), budget=20000000)
        self.assertEqual((result["status"], result["output"]), ("end", "101"))

    def test_nested_reflection_and_rule30(self):
        guest = compile_program(step_function())
        for levels in (0, 1, 2, 8):
            decoder = self.reflected
            for _ in range(levels):
                decoder = app(decoder, bitlist(""))
            result = read_bits(app(decoder, bitlist(guest), bitlist("00100")), budget=20000000)
            self.assertEqual((result["status"], result["output"]), ("end", "01110"))

    def test_rule30_trajectory(self):
        guest = compile_program(step_function())
        row = "0000001000000"
        for expected in ("0000011100000", "0000110010000", "0001101111000",
                         "0011001000100", "0110111101110"):
            result = read_bits(app(self.reflected, bitlist(guest), bitlist(row)), budget=20000000)
            self.assertEqual((result["status"], result["output"]), ("end", expected))
            row = result["output"]

    def test_artifacts(self):
        root = ROOT
        saved = json.loads((root / "artifacts/knot/metrics.json").read_text())
        self.assertEqual(json.loads(json.dumps(report())), saved)
        self.assertEqual((root / "artifacts/knot/kernel.blc").read_text(), encode(self.reflected))
        self.assertEqual((root / "artifacts/knot/self.bits").read_bytes(), b"")
        self.assertEqual((root / "artifacts/knot/rule30.bits").read_text(), compile_program(step_function()))
        self.assertEqual(len(compile_program(step_function())), 809)


if __name__ == "__main__":
    unittest.main()
