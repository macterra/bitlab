import hashlib
import itertools
import json
import unittest
from functools import lru_cache
from pathlib import Path

from functional import (FALSE, IDENTITY, NIL, OMEGA, TRUE, Machine, app, beta,
                        bitlist, closed, contract_at, encode, lam, named,
                        normalize, parse, read_bits)
from functional_candidates import decoder, parser_seed, program, search, tromp_parser


@lru_cache(maxsize=None)
def terms(size, depth=0):
    """Independently enumerate all closed BLC terms at a small exact bit size."""
    result = []
    if 0 <= size - 2 < depth:
        result.append(size - 2)
    if size >= 4:
        result.extend(lam(body) for body in terms(size - 2, depth + 1))
    for left_size in range(2, size - 3):
        result.extend(app(left, right)
                      for left in terms(left_size, depth)
                      for right in terms(size - 2 - left_size, depth))
    return tuple(result)


class FunctionalTests(unittest.TestCase):
    def test_reference_binding_and_substitution(self):
        self.assertEqual(named(r"\x y. x"), lam(lam(1)))
        self.assertEqual(named(r"\x. (\y. x)"), lam(lam(1)))
        self.assertEqual(beta(lam(1), 0), lam(1))  # Open argument is not captured.
        self.assertEqual(normalize(app(TRUE, IDENTITY, OMEGA)), IDENTITY)
        self.assertEqual(normalize(app(FALSE, OMEGA, IDENTITY)), IDENTITY)
        self.assertEqual(Machine(OMEGA).run(1000), "suspended")

    def test_calibration(self):
        self.assertEqual(len(encode(parser_seed())), 187)
        self.assertEqual(len(encode(tromp_parser())), 168)
        self.assertEqual(len(encode(decoder())), 174)
        best, report = search(parser_seed(), rounds=20, beam=256, slack=150)
        replay = parser_seed()
        for path in report["beta_paths"]:
            replay = contract_at(replay, path)
        self.assertEqual(replay, best)
        self.assertEqual(best, tromp_parser())
        self.assertTrue(closed(best))

    def test_valid_closed_terms_against_native_evaluation(self):
        count = 0
        for size in range(4, 17):
            for term in terms(size):
                count += 1
                bits = encode(term)
                self.assertEqual(len(bits), size)
                self.assertEqual(parse(bits), (term, ""))
                self.assertTrue(closed(term))
                self.assertEqual(normalize(app(decoder(), bitlist(bits))), normalize(term))
        self.assertGreater(count, 100)

    def test_every_bitstring_through_eight_bits(self):
        for length in range(9):
            for digits in itertools.product("01", repeat=length):
                bits = "".join(digits)
                term = program(bits)
                self.assertTrue(closed(term))
                self.assertIn(Machine(term).run(5000), ("value", "suspended"))

    def test_eof_and_suffix_contract(self):
        for bits in ("", "0", "1", "00", "01"):
            # These particular incomplete sources act as identity, not errors.
            self.assertEqual(normalize(app(decoder(), bitlist(bits))), IDENTITY)
        for suffix in ("", "0", "111", "0001101"):
            self.assertEqual(normalize(app(decoder(), bitlist(encode(TRUE) + suffix))), TRUE)

    def test_complete_self_interpretation(self):
        self_bits = encode(decoder())
        inputs = (NIL, TRUE, FALSE, bitlist("101"))
        guests = ("", "0", "1", "11", encode(IDENTITY), encode(TRUE), encode(FALSE))
        for bits in guests:
            for argument in inputs:
                direct = program(bits, argument)
                nested = app(program(self_bits, bitlist(bits)), argument)
                self.assertEqual(normalize(nested, 200000), normalize(direct, 200000))
        # Two full levels of self-interpretation, not merely a prefix smoke test.
        two_levels = app(program(self_bits, bitlist(self_bits)),
                         bitlist(encode(IDENTITY)), bitlist("101"))
        self.assertEqual(read_bits(two_levels, budget=2000000)["output"], "101")
        self.assertEqual(read_bits(two_levels, budget=2000000)["status"], "end")

    def test_computation_io_and_divergence(self):
        negate_list_head = named(r"\xs. xs (\head tail f. f (head false true) tail)",
                                 {"false": FALSE, "true": TRUE})
        computation = program(encode(negate_list_head), bitlist("101"))
        self.assertEqual(read_bits(computation)["output"], "001")
        self.assertEqual(read_bits(program(encode(IDENTITY), bitlist("101")))["output"], "101")
        machine = Machine(program(encode(OMEGA)))
        self.assertEqual(machine.run(10000), "suspended")
        self.assertEqual(machine.run(10000), "suspended")
        self.assertEqual(machine.steps, 20000)

    def test_reproducible_artifact_and_search_certificate(self):
        root = Path(__file__).parent
        saved = json.loads((root / "functional_metrics.json").read_text())
        best, report = search(decoder())
        replay = decoder()
        for path in report["beta_paths"]:
            replay = contract_at(replay, path)
        self.assertEqual(replay, best)
        bits = encode(best)
        self.assertEqual(bits, (root / "functional_self.blc").read_text())
        self.assertEqual(saved["bits"], len(bits))
        self.assertEqual(saved["search"], json.loads(json.dumps(report)))
        self.assertEqual(saved["sha256"], hashlib.sha256(bits.encode()).hexdigest())
        reference = (root / "functional.py").read_bytes()
        self.assertEqual(saved["reference_python_bytes"], len(reference))
        self.assertEqual(saved["reference_python_sha256"], hashlib.sha256(reference).hexdigest())
        self.assertEqual(parse(bits), (best, ""))


if __name__ == "__main__":
    unittest.main()
