from core.artifacts import ROOT, repo_path
import copy
import hashlib
import itertools
import json
import unittest
from pathlib import Path

from core.lambda_calculus import IDENTITY, OMEGA, app, bitlist, closed, contractions, encode, lam, named, normalize, parse, read_bits
from experiments.functional_candidates import decoder, parser_seed, program
from core.rewrites import at, extract, neighbors, outward, replay, search, size, choose
from experiments.rewrite_search import source_proof
from tests.test_functional import terms


class RewriteTests(unittest.TestCase):
    def test_scope_and_capture(self):
        # The helper refers to an outer variable across two intervening binders.
        self.assertEqual(outward(lam(app(0, 3)), 2), lam(app(0, 1)))
        with self.assertRaises(ValueError):
            outward(lam(app(0, 2)), 2)
        term = named(r"\x. x (\y. x)")
        body = term[1]
        expanded = extract(body, 0, [(1,), (2, 1)])
        step = dict(rule="expand", path=[1], replacement=encode(expanded))
        result = replay(term, [step])
        self.assertTrue(closed(result))
        self.assertEqual(normalize(result), term)
        with self.assertRaises(ValueError):
            extract(body, 0, [(2,)])
        with self.assertRaises(ValueError):
            at(term, [2])

    def test_generated_rewrites_replay_and_preserve_normal_forms(self):
        examples = [term for bits in range(4, 15) for term in terms(bits)]
        examples += [named(r"(\x y. x (\z. z y)) (\a. a) (\b. b)"),
                     named(r"\a b. (\x y. x a y) a b")]
        checked, kinds = 0, set()
        for term in examples:
            expected = normalize(term)
            self.assertEqual(size(term), len(encode(term)))
            for changed, step in neighbors(term, subsets=True):
                checked += 1
                kinds.add(step["rule"])
                self.assertEqual(replay(term, [step]), changed)
                self.assertEqual(normalize(changed), expected)
                self.assertEqual(size(changed), len(encode(changed)))
        self.assertGreater(checked, 100)
        self.assertEqual(kinds, {"contract", "expand", "join"})

    def test_checker_rejects_corrupt_certificates(self):
        seed = named(r"(\x y. x) (\a. a) (\b c. b)")
        steps = list(neighbors(seed))
        for _, step in steps:
            if step["rule"] in ("expand", "join"):
                corrupt = copy.deepcopy(step)
                corrupt["replacement"] = encode(IDENTITY)
                with self.assertRaises(ValueError):
                    replay(seed, [corrupt])
        with self.assertRaises(ValueError):
            replay(seed, [dict(rule="contract", path=[0])])
        with self.assertRaises(ValueError):
            replay(seed, [dict(rule="magic", path=[])])
        valid = next(step for _, step in steps if step["rule"] == "expand")
        corrupt = dict(valid, replacement=valid["replacement"] + "0")
        with self.assertRaises(ValueError):
            replay(seed, [corrupt])

    def test_factoring_improves_a_beta_normal_term(self):
        # A contraction-only search has no moves; introducing a helper saves bits.
        seed = named(r"\f. f (\a b c d e. a (b (c (d e)))) (\a b c d e. a (b (c (d e))))")
        self.assertEqual(list(contractions(seed)), [])
        best, report = search(seed, rounds=2, beam=8, slack=20)
        self.assertLess(size(best), size(seed))
        self.assertTrue(any(step["rule"] == "expand" for step in report["proof"]))
        self.assertEqual(normalize(best), seed)
        self.assertEqual(replay(seed, report["proof"]), best)
        self.assertEqual(search(seed, rounds=2, beam=8, slack=20)[1], report)

    def test_unused_divergent_arguments_remain_lazy(self):
        seed = app(lam(IDENTITY), OMEGA)
        for changed, step in neighbors(seed):
            self.assertEqual(replay(seed, [step]), changed)
            self.assertEqual(normalize(changed, 10000), IDENTITY)

    def test_source_start_layers_and_limits(self):
        proof = source_proof()
        self.assertEqual(replay(decoder(), proof), app(parser_seed(), IDENTITY))
        self.assertGreater(size(replay(decoder(), proof)), size(decoder()))
        candidates = [(bits, str(index), index, []) for index, bits in enumerate((10, 10, 10, 12, 14))]
        self.assertEqual([row[0] for row in choose(candidates, 3, "layers")], [10, 12, 14])
        _, report = search(decoder(), rounds=10, max_generated=3)
        self.assertEqual(report["generated"], 3)
        self.assertEqual(report["stop_reason"], "candidate limit")
        _, report = search(decoder(), rounds=0, start_proofs=[proof])
        self.assertEqual(report["result_bits"], 174)
        for options in (dict(beam=0), dict(slack=-1), dict(rounds=-1),
                        dict(policy="unknown"), dict(max_generated=0)):
            with self.assertRaises(ValueError):
                search(decoder(), **options)

    def test_saved_artifact_proof_and_execution(self):
        root = ROOT
        report = json.loads((root / "artifacts/searches/rewrites/metrics.json").read_text())
        bits = (root / "artifacts/searches/rewrites/self.blc").read_text()
        best = replay(decoder(), report["proof"])
        self.assertEqual(parse(bits), (best, ""))
        self.assertEqual(size(best), report["result_bits"])
        self.assertEqual(hashlib.sha256(bits.encode()).hexdigest(), report["sha256"])
        self.assertEqual(hashlib.sha256(encode(decoder()).encode()).hexdigest(), report["seed_sha256"])
        source = b"".join((root / name).read_bytes() for name in report["search_files"])
        self.assertEqual(len(source), report["search_source_bytes"])
        self.assertEqual(hashlib.sha256(source).hexdigest(), report["search_source_sha256"])
        for run in report["runs"]:
            result = replay(decoder(), run["proof"])
            self.assertEqual(size(result), run["result_bits"])
            for proof in run["start_proofs"]:
                self.assertTrue(closed(replay(decoder(), proof)))
        # Compare arbitrary raw sources; no conventional BLC validity filter.
        for length in range(6):
            for digits in itertools.product("01", repeat=length):
                guest = "".join(digits)
                self.assertEqual(normalize(app(best, bitlist(guest)), 200000),
                                 normalize(app(decoder(), bitlist(guest)), 200000))
        # Complete two interpretation levels using the actual emitted artifact.
        nested = app(program(bits, bitlist(bits)), bitlist(encode(IDENTITY)), bitlist("101"))
        result = read_bits(nested, budget=3000000)
        self.assertEqual((result["status"], result["output"]), ("end", "101"))


if __name__ == "__main__":
    unittest.main()
