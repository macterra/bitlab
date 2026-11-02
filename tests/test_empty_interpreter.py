from core.artifacts import ROOT, repo_path
import hashlib
import itertools
import json
import unittest
from pathlib import Path

from experiments.empty_interpreter import build, seed
from core.lambda_calculus import IDENTITY, Machine, app, bitlist, closed, encode, named, normalize, read_bits
from experiments.functional_candidates import decoder
from core.rewrites import replay


class EmptyInterpreterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel, cls.report = build()

    def test_nonempty_sources_preserved(self):
        for length in range(1, 7):
            for digits in itertools.product("01", repeat=length):
                source = bitlist("".join(digits))
                self.assertEqual(normalize(app(self.kernel, source)), normalize(app(decoder(), source)))

    def test_empty_source_interprets_arbitrary_guests(self):
        for guest in ("", "0", "1", "11", encode(IDENTITY), encode(named(r"\x y. x"))):
            source = bitlist(guest)
            direct = app(self.kernel, source, bitlist("101"))
            interpreted = app(self.kernel, bitlist(""), source, bitlist("101"))
            # The empty guest returns a decoder, whose full normal form need not exist.
            # Apply both to a concrete closed-program source to observe that case.
            if guest == "":
                direct = app(self.kernel, source, bitlist(encode(IDENTITY)), bitlist("101"))
                interpreted = app(self.kernel, bitlist(""), source, bitlist(encode(IDENTITY)), bitlist("101"))
            self.assertEqual(normalize(direct, 200000), normalize(interpreted, 200000))

    def test_nested_empty_interpreters_and_computation(self):
        flip = named(r"\xs. xs (\head tail f. f (head (\a b. b) (\a b. a)) tail)")
        for levels in (0, 1, 2, 8):
            term = self.kernel
            for _ in range(levels):
                term = app(term, bitlist(""))
            result = read_bits(app(term, bitlist(encode(flip)), bitlist("101")), budget=2000000)
            self.assertEqual((result["status"], result["output"]), ("end", "001"))

    def test_all_short_sources_are_closed(self):
        for length in range(8):
            for digits in itertools.product("01", repeat=length):
                term = app(self.kernel, bitlist("".join(digits)))
                self.assertTrue(closed(term))
                self.assertIn(Machine(term).run(5000), ("value", "suspended"))

    def test_artifacts_and_certificate(self):
        root = ROOT
        saved = json.loads((root / "artifacts/functional/empty_metrics.json").read_text())
        for key, value in self.report.items():
            self.assertEqual(json.loads(json.dumps(value)), saved[key])
        self.assertEqual(replay(seed(), saved["proof"]), self.kernel)
        self.assertEqual((root / "artifacts/functional/empty_self.bits").read_bytes(), b"")
        self.assertEqual((root / "artifacts/functional/empty_kernel.blc").read_text(), encode(self.kernel))
        source = b"".join((root / name).read_bytes() for name in saved["source_files"])
        self.assertEqual(hashlib.sha256(source).hexdigest(), saved["source_sha256"])


if __name__ == "__main__":
    unittest.main()
