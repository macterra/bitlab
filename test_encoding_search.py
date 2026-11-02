import hashlib
import itertools
import json
import unittest
from pathlib import Path

from encoding_search import BASELINE, Encoding, decoder_seed, family, optimize, parser_seed
from functional import (FALSE, IDENTITY, NIL, TRUE, Machine, app, bitlist, closed,
                        encode, lam, named, normalize, read_bits)
from functional_candidates import decoder, parser_seed as original_parser_seed
from functional_rewrites import positions, replay
from test_functional import terms


class EncodingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parent
        cls.report = json.loads((cls.root / "encoding_metrics.json").read_text())
        cls.rows = cls.report["candidates"]
        cls.kernels = {row["key"]: replay(decoder_seed(Encoding(**row["encoding"])), row["proof"])
                       for row in cls.rows}
        cls.examples = [term for size in range(4, 17) for term in terms(size)]

    def test_family_and_native_codec(self):
        variants = family()
        self.assertEqual(len(variants), 24)
        self.assertEqual(len(set(variants)), 24)
        self.assertEqual({row["key"] for row in self.rows}, {e.key for e in variants})
        for e in variants:
            size = e.scorer()
            for term in self.examples + [0, 1, 15, 127]:
                bits = e.encode(term)
                self.assertEqual(size(term), len(bits))
                self.assertEqual(e.parse(bits), (term, ""))
                self.assertEqual(e.parse(bits + "101"), (term, "101"))
            with self.assertRaises(ValueError):
                e.parse(e.variable)
            with self.assertRaises(ValueError):
                e.parse("2")
        for term in self.examples:
            self.assertEqual(BASELINE.encode(term), encode(term))
        with self.assertRaises(ValueError):
            Encoding("0", "0", "1", "1")

    def test_baseline_calibration(self):
        self.assertEqual(parser_seed(BASELINE), original_parser_seed())
        best, report = optimize(decoder_seed(BASELINE), BASELINE)
        self.assertEqual(len(BASELINE.encode(best)), 174)
        self.assertEqual(best, replay(decoder_seed(BASELINE), report["proof"]))
        # Exact artifact calibration, not just a coincidental equal length.
        self.assertEqual(best, decoder())

    def test_every_small_closed_term_in_every_language(self):
        self.assertEqual(len(self.examples), 226)
        for row in self.rows:
            e = Encoding(**row["encoding"])
            kernel = self.kernels[e.key]
            for term in self.examples:
                expected = normalize(term)
                for suffix in ("", "101"):
                    source = bitlist(e.encode(term) + suffix)
                    self.assertEqual(normalize(app(kernel, source), 200000), expected, e.key)

    def test_open_terms_and_exact_remainder(self):
        values = (TRUE, FALSE, IDENTITY)
        examples = [0, 1, 2, lam(1), lam(app(1, 0)), lam(lam(app(3, 0)))]

        def substitute(term, depth=0):
            if isinstance(term, int):
                return term if term < depth else values[term - depth]
            if term[0] == "L":
                return lam(substitute(term[1], depth + 1))
            return app(substitute(term[1], depth), substitute(term[2], depth))

        for e in family():
            cons = named(r"\head tail choose rest. choose head (rest tail)" if e.repeat == "1" else
                         r"\head tail choose rest. choose (rest tail) head")
            environment = NIL
            for value in reversed(values):
                environment = app(cons, value, environment)
            continuation = named(r"\body rest. body env", {"env": environment})
            parser = parser_seed(e)
            for term in examples:
                source = bitlist(e.encode(term) + "101")
                actual = app(parser, continuation, source)
                self.assertEqual(normalize(actual, 200000), normalize(substitute(term)), e.key)
                remainder = app(parser, FALSE, source)
                self.assertEqual(normalize(remainder, 200000), normalize(bitlist("101")), e.key)

    def test_arbitrary_sources_have_defined_execution(self):
        for row in self.rows:
            kernel = self.kernels[row["key"]]
            self.assertTrue(closed(kernel))
            for length in range(7):
                for digits in itertools.product("01", repeat=length):
                    term = app(kernel, bitlist("".join(digits)))
                    self.assertTrue(closed(term))
                    self.assertIn(Machine(term).run(2000), ("value", "suspended"))

    def test_native_self_interpretation_and_computation(self):
        flip = named(r"\xs. xs (\head tail f. f (head false true) tail)",
                     {"false": FALSE, "true": TRUE})
        for row in self.rows:
            e = Encoding(**row["encoding"])
            kernel, bits = self.kernels[e.key], row["artifact"]
            # The interpreter is decoded from its own native bits.
            interpreted = app(kernel, bitlist(bits))
            for guest in ("", "0", "1", e.encode(IDENTITY), e.encode(TRUE)):
                direct = app(kernel, bitlist(guest), bitlist("101"))
                nested = app(interpreted, bitlist(guest), bitlist("101"))
                self.assertEqual(normalize(nested, 1000000), normalize(direct, 1000000), e.key)
            computation = app(interpreted, bitlist(e.encode(flip)), bitlist("101"))
            result = read_bits(computation, budget=3000000)
            self.assertEqual((result["status"], result["output"]), ("end", "001"), e.key)
            # Two complete interpretation levels, including the native artifact twice.
            twice = app(interpreted, bitlist(bits), bitlist(e.encode(IDENTITY)), bitlist("101"))
            result = read_bits(twice, budget=5000000)
            self.assertEqual((result["status"], result["output"]), ("end", "101"), e.key)

    def test_native_cost_identities(self):
        application_short = Encoding("10", "0", "11", "1")
        abstraction_short = Encoding("0", "10", "11", "0")
        for term in self.examples:
            counts = {"V": 0, "L": 0, "A": 0}
            for _, node, _ in positions(term):
                counts["V" if isinstance(node, int) else node[0]] += 1
            self.assertEqual(counts["V"], counts["A"] + 1)
            self.assertEqual(len(application_short.encode(term)), len(encode(term)) + 1)
            self.assertEqual(len(abstraction_short.encode(term)), len(encode(term)) + counts["V"] - counts["L"])

    def test_native_search_limits_and_positive_control(self):
        e = Encoding("0", "10", "11", "1")
        term = named(r"\f. f (\a b c d e. a (b (c (d e)))) (\a b c d e. a (b (c (d e))))")
        best, report = optimize(term, e, mode="rewrite", rounds=2, beam=8, slack=20)
        self.assertLess(len(e.encode(best)), len(e.encode(term)))
        self.assertEqual(normalize(best), term)
        self.assertEqual(best, replay(term, report["proof"]))
        self.assertEqual(optimize(term, e, mode="rewrite", rounds=2, beam=8, slack=20)[1], report)
        _, limited = optimize(term, e, mode="rewrite", max_generated=3)
        self.assertEqual(limited["generated"], 3)
        self.assertEqual(limited["stop_reason"], "candidate limit")

    def test_report_proofs_hashes_and_artifacts(self):
        report = self.report
        self.assertEqual(report["variants"], len(self.rows))
        self.assertEqual(report["best_key"], self.rows[0]["key"])
        self.assertEqual(report["best_bits"], min(row["native_bits"] for row in self.rows))
        self.assertEqual((self.root / "encoding_self.bits").read_text(), self.rows[0]["artifact"])
        self.assertEqual(report["generated_across_variants"],
                         sum(phase["generated"] for row in self.rows for phase in row["phases"]))
        source = b"".join((self.root / name).read_bytes() for name in report["source_files"])
        self.assertEqual(len(source), report["source_bytes"])
        self.assertEqual(hashlib.sha256(source).hexdigest(), report["source_sha256"])
        for row in self.rows:
            e = Encoding(**row["encoding"])
            kernel, bits = self.kernels[e.key], row["artifact"]
            self.assertEqual(e.encode(kernel), bits)
            self.assertEqual(e.parse(bits), (kernel, ""))
            self.assertEqual(row["native_bits"], len(bits))
            self.assertEqual(row["blc_bits"], len(encode(kernel)))
            self.assertEqual(row["sha256"], hashlib.sha256(bits.encode()).hexdigest())
            stage = decoder_seed(e)
            for phase in row["phases"]:
                self.assertEqual(phase["seed_bits"], len(e.encode(stage)))
                stage = replay(stage, phase["proof"])
                self.assertEqual(phase["result_bits"], len(e.encode(stage)))
                self.assertEqual(phase["generated"], sum(phase["rules"].values()))
            self.assertEqual(stage, kernel)


if __name__ == "__main__":
    unittest.main()
