import hashlib
import itertools
import json
import unittest
from pathlib import Path

from bitfold import compile_sk, interpreter, meaning, native_encode
from functional import (IDENTITY, Machine, app, bitlist, closed, encode, lam,
                        named, normalize, parse, read_bits)
from functional_rewrites import replay
from reflective_fold import build, reflection_seed, survey


class ReflectiveFoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = [build(basis) for basis in ("SK", "KSK")]

    def encode_guest(self, term, row):
        words = row["certificate"]["words"]
        return native_encode(compile_sk(term, words), words, reverse=True)

    def test_fixed_point_certificates(self):
        for base, reflected, row in self.candidates:
            original = interpreter(constants=row["basis"], reverse=True, shared=True)
            self.assertEqual(replay(original, row["proof"]), base)
            self.assertEqual(replay(reflection_seed(base), row["reflection_proof"]), reflected)
            self.assertTrue(closed(base))
            self.assertTrue(closed(reflected))

    def test_nonempty_semantics_preserved(self):
        for base, reflected, row in self.candidates:
            for length in range(1, 7):
                for digits in itertools.product("01", repeat=length):
                    bits = "".join(digits)
                    expected = normalize(meaning(bits, constants=row["basis"], reverse=True))
                    self.assertEqual(normalize(app(base, bitlist(bits))), expected)
                    self.assertEqual(normalize(app(reflected, bitlist(bits))), expected)

    def test_universal_embedding_and_nonempty_codes(self):
        examples = (IDENTITY, named(r"\x y. x"), named(r"\x y. y"),
                    named(r"\f x. f (f x)"), named(r"\a b c. a c (b c)"))
        for base, reflected, row in self.candidates:
            for term in examples:
                bits = self.encode_guest(term, row)
                self.assertTrue(bits)
                self.assertEqual(normalize(app(base, bitlist(bits))), normalize(term))
                self.assertEqual(normalize(app(reflected, bitlist(bits))), normalize(term))

    def test_ordinary_native_self_interpreters(self):
        for base, _, row in self.candidates:
            guest = self.encode_guest(IDENTITY, row)
            term = app(base, bitlist(row["ordinary_self_program"]), bitlist(guest), bitlist("101"))
            result = read_bits(term, budget=10000000)
            self.assertEqual((result["status"], result["output"]), ("end", "101"))

    def test_zero_bit_interpreters_nested_and_compute(self):
        flip = named(r"\xs. xs (\head tail f. f (head (\a b. b) (\a b. a)) tail)")
        for _, reflected, row in self.candidates:
            guest = self.encode_guest(flip, row)
            for levels in (0, 1, 2, 8):
                term = reflected
                for _ in range(levels):
                    term = app(term, bitlist(""))
                result = read_bits(app(term, bitlist(guest), bitlist("101")), budget=1000000)
                self.assertEqual((result["status"], result["output"]), ("end", "001"))

    def test_all_short_sources_defined(self):
        for _, reflected, _ in self.candidates:
            for length in range(8):
                for digits in itertools.product("01", repeat=length):
                    term = app(reflected, bitlist("".join(digits)))
                    self.assertTrue(closed(term))
                    self.assertIn(Machine(term).run(5000), ("value", "suspended"))

    def test_artifacts_and_sizes(self):
        root = Path(__file__).parent
        saved = json.loads((root / "reflective_metrics.json").read_text())
        self.assertEqual(json.loads(json.dumps(survey())), saved)
        self.assertEqual(saved["best_kernel_bits"], 155)
        self.assertEqual(saved["best_self_bits"], 0)
        self.assertEqual((root / "reflective_self.bits").read_bytes(), b"")
        bits = (root / "reflective_kernel.blc").read_text()
        self.assertEqual(bits, saved["candidates"][0]["reflective_kernel_blc"])
        self.assertTrue(closed(parse(bits)[0]))
        for base, reflected, row in self.candidates:
            self.assertEqual(len(encode(reflected)), row["reflective_kernel_bits"])
            self.assertEqual(len(encode(base)), row["ordinary_kernel_bits"])
            self.assertEqual(len(row["ordinary_self_program"]), row["ordinary_self_bits"])
            self.assertEqual(hashlib.sha256(encode(reflected).encode()).hexdigest(), row["reflective_kernel_sha256"])


if __name__ == "__main__":
    unittest.main()
