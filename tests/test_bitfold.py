from core.artifacts import ROOT, repo_path
import hashlib
import itertools
import json
import unittest
from pathlib import Path

from core.combinators import K, S, SK_B, SK_C, compile_sk, sk_lambda
from languages.bitfold import certificate, interpreter, meaning, measure, native_encode, survey
from core.lambda_calculus import IDENTITY, Machine, app, bitlist, closed, lam, named, normalize, read_bits


class BitfoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        cls.report = json.loads((cls.root / "artifacts/bitfold/metrics.json").read_text())
        cls.certificates = [c for c in cls.report["certificates"] if c["certified"]]

    def test_constructive_certificates(self):
        self.assertEqual({c["constants"] for c in self.certificates}, {"SK", "KSK"})
        for cert in self.certificates:
            for name, target in (("K", K), ("S", S)):
                actual = lam(meaning(cert["words"][name], cert["constants"], initial=0))
                self.assertEqual(normalize(actual), normalize(lam(app(0, target))))
            word = "1" + cert["words"]["K"] + cert["words"]["S"]
            actual = lam(meaning(word, cert["constants"], initial=0))
            self.assertEqual(normalize(actual), normalize(lam(app(0, app(K, S)))))

    def test_all_bits_have_closed_meanings(self):
        for cert in self.certificates:
            for length in range(9):
                for digits in itertools.product("01", repeat=length):
                    term = meaning("".join(digits), cert["constants"])
                    self.assertTrue(closed(term))
                    self.assertIn(Machine(term).run(10000), ("value", "suspended"))

    def test_fold_definitions_in_all_certified_languages(self):
        for cert in self.certificates:
            for swapped, reverse in itertools.product((False, True), repeat=2):
                options = dict(constants=cert["constants"], swapped=swapped, reverse=reverse)
                fold = interpreter(**options)
                for length in range(6):
                    for digits in itertools.product("01", repeat=length):
                        bits = "".join(digits)
                        self.assertEqual(normalize(app(fold, bitlist(bits))),
                                         normalize(meaning(bits, **options)))

    def test_bracket_abstraction_and_native_encoding(self):
        self.assertEqual(normalize(sk_lambda(SK_B)), named(r"\f g x. f (g x)"))
        self.assertEqual(normalize(sk_lambda(SK_C)), named(r"\f x y. f y x"))
        examples = (IDENTITY, K, S, named(r"\f x. f (f x)"),
                    named(r"\a b c. c b a"), named(r"\f g x. g (f x)"))
        for cert in self.certificates:
            for term in examples:
                for optimize in (False, True):
                    tree = compile_sk(term, cert["words"], optimize)
                    self.assertEqual(normalize(sk_lambda(tree)), normalize(term))
                    for swapped, reverse in itertools.product((False, True), repeat=2):
                        bits = native_encode(tree, cert["words"], swapped, reverse)
                        self.assertEqual(normalize(meaning(bits, cert["constants"], swapped, reverse)),
                                         normalize(term))

    def test_emitted_self_interpreters(self):
        # Every measured implementation executes as a native bitstring.
        for row in self.report["candidates"]:
            cert = next(c for c in self.certificates if c["constants"] == row["constants"])
            args = [row[k] for k in ("swapped", "reverse", "shared", "optimize")]
            bits, measured = measure(cert, *args)
            self.assertEqual(row, measured)
            options = {k: row[k] for k in ("constants", "swapped", "reverse")}
            for guest in ("", "0", "1", "000"):
                native = app(meaning(bits, **options), bitlist(guest), bitlist("101"))
                direct = app(meaning(guest, **options), bitlist("101"))
                self.assertEqual(normalize(native, 1000000), normalize(direct, 1000000))

    def test_complete_self_interpretation_and_computation(self):
        best = self.report["candidates"][0]
        options = {k: best[k] for k in ("constants", "swapped", "reverse")}
        cert = next(c for c in self.certificates if c["constants"] == best["constants"])
        bits = (self.root / "artifacts/bitfold/self.bits").read_text()
        # A real bit-list computation, compiled to the same native language.
        flip_head = named(r"\xs. xs (\head tail f. f (head false true) tail)",
                          {"false": named(r"\a b. b"), "true": K})
        guest = native_encode(compile_sk(flip_head, cert["words"]), cert["words"],
                              best["swapped"], best["reverse"])
        direct = read_bits(app(meaning(guest, **options), bitlist("101")), budget=1000000)
        # Call-by-name duplicates work; this completed case takes ~9.8M steps.
        nested = read_bits(app(meaning(bits, **options), bitlist(guest), bitlist("101")), budget=15000000)
        self.assertEqual((direct["status"], direct["output"]), ("end", "001"))
        self.assertEqual((nested["status"], nested["output"]), ("end", "001"))

    def test_survey_and_artifacts_reproduce(self):
        self.assertEqual(survey(), self.report)
        best = self.report["candidates"][0]
        artifact = (self.root / "artifacts/bitfold/self.bits").read_text()
        self.assertEqual(len(artifact), best["native_bits"])
        self.assertEqual(hashlib.sha256(artifact.encode()).hexdigest(), best["sha256"])
        baseline, report = measure(certificate())
        self.assertEqual(baseline, (self.root / "artifacts/bitfold/jot_self.bits").read_text())
        self.assertEqual(report, json.loads((self.root / "artifacts/bitfold/jot_metrics.json").read_text()))

    def test_search_failure_is_not_a_nonuniversality_claim(self):
        too_short = certificate("SK", max_length=2)
        self.assertFalse(too_short["certified"])
        self.assertEqual(too_short["checked"], 7)
        self.assertEqual(too_short["words"], {})


if __name__ == "__main__":
    unittest.main()
