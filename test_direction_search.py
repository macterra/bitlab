import itertools
import json
import unittest
from pathlib import Path

from bitfold import compile_sk, interpreter, meaning, native_encode
from direction_search import forward, survey
from functional import IDENTITY, app, bitlist, closed, named, normalize, read_bits
from functional_rewrites import replay
from reflective_fold import build, reflection_seed


class DirectionSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = [forward(basis) for basis in ("SK", "KSK")]

    def test_proofs_and_empty_ordinary_source(self):
        for base, reflected, row in self.candidates:
            original = interpreter(constants=row["basis"], reverse=False)
            self.assertEqual(replay(original, row["proof"]), base)
            self.assertEqual(replay(reflection_seed(base), row["reflection_proof"]), reflected)
            self.assertTrue(closed(base))
            self.assertTrue(closed(reflected))
            self.assertEqual(normalize(app(base, bitlist(""))), IDENTITY)

    def test_short_sources_and_reversal(self):
        for base, reflected, row in self.candidates:
            backward, backward_reflected, _ = build(row["basis"])
            for length in range(1, 7):
                for digits in itertools.product("01", repeat=length):
                    bits = "".join(digits)
                    expected = normalize(meaning(bits, constants=row["basis"]))
                    for kernel, source in ((base, bits), (reflected, bits),
                                           (backward, bits[::-1]), (backward_reflected, bits[::-1])):
                        self.assertEqual(normalize(app(kernel, bitlist(source))), expected)

    def test_native_self_interpreters_and_nested_reflection(self):
        flip = named(r"\xs. xs (\head tail f. f (head (\a b. b) (\a b. a)) tail)")
        for base, reflected, row in self.candidates:
            words = row["certificate"]["words"]
            guest = native_encode(compile_sk(flip, words), words)
            self.assertTrue(guest)
            ordinary = app(base, bitlist(row["ordinary_self_program"]), bitlist(guest), bitlist("101"))
            result = read_bits(ordinary, budget=100000000)
            self.assertEqual((result["status"], result["output"]), ("end", "001"))
            for levels in (0, 1, 2, 8):
                term = reflected
                for _ in range(levels):
                    term = app(term, bitlist(""))
                result = read_bits(app(term, bitlist(guest), bitlist("101")), budget=1000000)
                self.assertEqual((result["status"], result["output"]), ("end", "001"))

    def test_reproducible_artifacts_and_matched_budgets(self):
        saved = json.loads(Path(__file__).with_name("direction_metrics.json").read_text())
        self.assertEqual(json.loads(json.dumps(survey())), saved)
        for left, right in zip(saved["candidates"][::2], saved["candidates"][1::2]):
            for stage in ("reduction", "reflection_reduction", "kernel_rewrite"):
                for setting in ("rounds", "beam", "slack"):
                    self.assertEqual(left[stage][setting], right[stage][setting])
            for setting in ("max_generated", "policy", "subsets"):
                self.assertEqual(left["kernel_rewrite"][setting], right["kernel_rewrite"][setting])
        self.assertEqual([(r["ordinary_kernel_bits"], r["reflective_kernel_bits"])
                          for r in saved["candidates"]], [(127, 168), (114, 155), (136, 177), (123, 164)])


if __name__ == "__main__":
    unittest.main()
