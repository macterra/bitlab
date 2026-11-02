import hashlib
import itertools
import json
import unittest
from pathlib import Path

from functional import app
from triage import (I, K, S, T, Machine, binary_interpreter, bitlist, compile_term,
                    encode, measure, normalize, parse, quote, read_bits, structural_interpreter)


def spine(term):
    arguments = []
    while isinstance(term, tuple):
        arguments.append(term[2])
        term = term[1]
    return term, list(reversed(arguments))


def reference_step(term):
    """Independent small-step rewriting; no demand stacks or machine frames."""
    head, args = spine(term)
    if head == T and len(args) >= 3:
        first, second, third = args[:3]
        tag, fields = spine(first)
        result = None
        if tag == T and not fields:
            result = second
        elif tag == T and len(fields) == 1:
            result = app(fields[0], third, app(second, third))
        elif tag == T and len(fields) == 2:
            tag, values = spine(third)
            if tag == T and len(values) <= 2:
                result = (fields[0] if not values else app(fields[1], values[0]) if len(values) == 1 else
                          app(second, values[0], values[1]))
        if result is not None:
            return app(result, *args[3:])
    if isinstance(term, tuple):
        left = reference_step(term[1])
        if left is not None:
            return app(left, term[2])
        right = reference_step(term[2])
        if right is not None:
            return app(term[1], right)
    return None


def reference_normalize(term, limit=10000):
    for _ in range(limit):
        result = reference_step(term)
        if result is None:
            return term
        term = result
    raise TimeoutError


class TriageTests(unittest.TestCase):
    def test_five_rules_and_independent_machine(self):
        cases = [app(T, T, I, K), app(T, app(T, K), I, S),
                 app(T, app(T, I, K), S, T),
                 app(T, app(T, I, K), S, app(T, I)),
                 app(T, app(T, I, K), S, app(T, I, K))]
        for term in cases:
            self.assertEqual(normalize(term), reference_normalize(term))
        for length in range(9):
            for digits in itertools.product("01", repeat=length):
                term, _ = parse("".join(digits))
                self.assertEqual(normalize(term), reference_normalize(term))

    def test_universal_basis_and_abstraction(self):
        for x in (T, I, K, S):
            self.assertEqual(normalize(app(I, x)), normalize(x))
            self.assertEqual(normalize(app(K, x, S)), normalize(x))
            self.assertEqual(normalize(app(S, K, K, x)), normalize(x))
        examples = [(r"\x. x", (K,), K),
                    (r"\x y. x", (I, K), I),
                    (r"\x y. y", (I, K), K),
                    (r"\f x. f (f x)", (I, K), K),
                    (r"\x y. T x y", (K, I), app(T, K, I))]
        for source, arguments, expected in examples:
            compiled = compile_term(source)
            self.assertEqual(normalize(app(compiled, *arguments)), normalize(expected))

    def test_codec_eof_and_every_short_raw_source(self):
        interpreter = binary_interpreter()
        for length in range(7):
            for digits in itertools.product("01", repeat=length):
                bits = "".join(digits)
                term, rest = parse(bits)
                self.assertEqual(parse(encode(term)), (term, ""))
                self.assertEqual(normalize(app(interpreter, bitlist(bits))), normalize(term))
        self.assertEqual(parse(""), (T, ""))
        self.assertEqual(parse("1"), (app(T, T), ""))
        self.assertEqual(parse("010101"), (T, "10101"))
        with self.assertRaises(ValueError):
            parse("2")

    def test_native_structural_self_interpretation(self):
        interpreter = structural_interpreter()
        for term in (T, I, K, S, app(S, K, K, I)):
            self.assertEqual(normalize(app(interpreter, quote(term))), normalize(term))
        nested = app(interpreter, quote(interpreter), quote(I), bitlist("101"))
        result = read_bits(nested, budget=10000000)
        self.assertEqual((result["status"], result["output"]), ("end", "101"))

    def test_native_raw_self_interpretation_and_computation(self):
        interpreter = binary_interpreter()
        bits = encode(interpreter)
        flip = compile_term(r"\xs. T (T T T) (\head tail. T (T (T (T T) (T T T)) T head) tail) xs")
        for program, expected in ((I, "101"), (flip, "001")):
            direct = read_bits(app(program, bitlist("101")))
            decoded = read_bits(app(interpreter, bitlist(encode(program)), bitlist("101")), budget=10000000)
            nested = read_bits(app(interpreter, bitlist(bits), bitlist(encode(program)), bitlist("101")),
                               budget=30000000)
            for result in (direct, decoded, nested):
                self.assertEqual((result["status"], result["output"]), ("end", expected))

    def test_resume_and_observation(self):
        term = app(binary_interpreter(), bitlist(encode(I)), bitlist("101"))
        machine = Machine(term)
        self.assertEqual(machine.run(1), "suspended")
        self.assertEqual(machine.run(1000000), "value")
        self.assertEqual(read_bits(machine.value())["output"], "101")
        for bits in ("", "0", "1", "10101"):
            result = read_bits(bitlist(bits))
            self.assertEqual((result["status"], result["output"]), ("end", bits))

    def test_artifacts_reproduce(self):
        root = Path(__file__).parent
        saved = json.loads((root / "triage_metrics.json").read_text())
        self.assertEqual(measure(), saved)
        for name, term, field in (("triage_self.bits", binary_interpreter(), "binary_sha256"),
                                  ("triage_structural.bits", structural_interpreter(), "structural_sha256")):
            bits = (root / name).read_text()
            self.assertEqual(bits, encode(term))
            self.assertEqual(parse(bits), (term, ""))
            self.assertEqual(hashlib.sha256(bits.encode()).hexdigest(), saved[field])


if __name__ == "__main__":
    unittest.main()
