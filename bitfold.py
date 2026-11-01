"""Bit-by-bit combinator languages, constructive certificates, and native scores.

The baseline is Barker's Jot: I initially, 0 maps f to f S K, and 1 maps
f to S(K f). Variants change the constants, bit polarity, and scan direction.
See BITFOLD.md. No evaluator primitive is available to guest programs.
"""

import argparse
import hashlib
import itertools
import json
from functools import lru_cache
from pathlib import Path

from functional import (IDENTITY, TRUE, app, bitlist, encode as blc_encode,
                        lam, named, normalize, read_bits)


S = named(r"\x y z. x z (y z)")
K = TRUE
B = named(r"\f x y. f (x y)")
CONSTANTS = {"S": S, "K": K, "I": IDENTITY}
SK_I = app("S", "K", "K")
SK_B = app("S", app("K", "S"), "K")
SK_C = app("S", app(SK_B, SK_B, "S"), app("K", "K"))


def step(state, bit, constants="SK", swapped=False):
    if (bit == "0") != swapped:
        return app(state, *(CONSTANTS[c] for c in constants))
    return app(S, app(K, state))


def meaning(bits, constants="SK", swapped=False, reverse=False, initial=IDENTITY):
    if any(bit not in "01" for bit in bits):
        raise ValueError("expected bits")
    for bit in reversed(bits) if reverse else bits:
        initial = step(initial, bit, constants, swapped)
    return initial


def certificate(constants="SK", max_length=10):
    """Find beta-normal-form witnesses F_word(a) = a K and a S.

    The symbolic accumulator is bound outside the entire computation. Thus a
    match checks all accumulators, not just a test suite of initial values.
    A timeout/absence is 'not certified within this bound', not nonuniversality.
    """
    targets = {normalize(lam(app(0, value))): name for name, value in (("K", K), ("S", S))}
    found = {}
    checked, timeouts = 0, 0
    for length in range(max_length + 1):
        for digits in itertools.product("01", repeat=length):
            bits = "".join(digits)
            checked += 1
            try:
                value = normalize(lam(meaning(bits, constants, initial=0)), budget=10000)
            except (TimeoutError, RecursionError):
                timeouts += 1
                continue
            if value in targets:
                found.setdefault(targets[value], bits)
                if len(found) == 2:
                    return dict(constants=constants, words=found, checked=checked,
                                timeouts=timeouts, max_length=max_length, certified=True)
    return dict(constants=constants, words=found, checked=checked, timeouts=timeouts,
                max_length=max_length, certified=False)


def native_encode(tree, words, swapped=False, reverse=False):
    pieces, pending = [], [tree]
    while pending:
        node = pending.pop()
        if node in ("S", "K"):
            pieces.append(words[node])
        elif isinstance(node, tuple) and node[0] == "A":
            pieces.append("1")
            pending.extend((node[2], node[1]))
        else:
            raise ValueError("expected a closed SK tree")
    bits = "".join(pieces)
    if swapped:
        bits = bits.translate(str.maketrans("01", "10"))
    return bits[::-1] if reverse else bits


def sk_lambda(tree):
    if tree == "S":
        return S
    if tree == "K":
        return K
    if isinstance(tree, int):
        return tree
    return app(sk_lambda(tree[1]), sk_lambda(tree[2]))


def compile_sk(term, words, optimize=True):
    """Bracket abstraction, with costed B/C alternatives; no eta contraction.

    All emitted nodes are S/K/application. B and C are expanded before scoring.
    The transformation preserves beta equivalence, including on arbitrary inputs.
    """
    @lru_cache(maxsize=None)
    def cost(node):
        if node in ("S", "K"):
            return len(words[node])
        if isinstance(node, int):
            return 0  # Every compared alternative has the same free occurrences.
        return 1 + cost(node[1]) + cost(node[2])

    @lru_cache(maxsize=None)
    def uses(node):
        return node == 0 if isinstance(node, int) else (
            False if isinstance(node, str) else uses(node[1]) or uses(node[2]))

    def lower(node):
        if isinstance(node, int):
            return node - 1
        if isinstance(node, str):
            return node
        return app(lower(node[1]), lower(node[2]))

    def abstract(node):
        if not uses(node):
            return app("K", lower(node))
        if node == 0:
            return SK_I
        left, right = node[1:]
        abstract_left, abstract_right = abstract(left), abstract(right)
        candidates = [app("S", abstract_left, abstract_right)]
        if optimize and not uses(left):
            candidates.append(app(SK_B, lower(left), abstract_right))
        if optimize and not uses(right):
            candidates.append(app(SK_C, abstract_left, lower(right)))
        return min(candidates, key=cost)

    def convert(node):
        if isinstance(node, int):
            return node
        if node[0] == "L":
            return abstract(convert(node[1]))
        return app(convert(node[1]), convert(node[2]))

    return convert(term)


def interpreter(constants="SK", swapped=False, reverse=False, shared=True):
    """A pure lambda fold over the existing raw boolean-pair list representation."""
    zero = "(acc " + " ".join(constants) + ")"
    one = "(S (K acc))"
    selection = f"(bit {one} {zero})" if swapped else f"(bit {zero} {one})"
    if reverse:
        selected = (rf"((\acc. {selection}) (self tail))" if shared else
                    selection.replace("acc", "(self tail)"))
        body = rf"\self bits. bits (\bit tail ignored. {selected}) I"
    else:
        body = rf"\self acc bits. bits (\bit tail ignored. self {selection} tail) acc"
    # Explicit fixed point; all its bits are included in the compiled artifact.
    fixed = named(r"\f. (\x. f (x x)) (\x. f (x x))")
    result = app(fixed, named(body, CONSTANTS))
    return result if reverse else app(result, IDENTITY)


def measure(cert, swapped=False, reverse=False, shared=True, optimize=True):
    term = interpreter(cert["constants"], swapped, reverse, shared)
    tree = compile_sk(term, cert["words"], optimize)
    bits = native_encode(tree, cert["words"], swapped, reverse)
    return bits, dict(constants=cert["constants"], swapped=swapped, reverse=reverse,
                      shared=shared, optimize=optimize, native_bits=len(bits),
                      lambda_bits=len(blc_encode(term)),
                      sha256=hashlib.sha256(bits.encode()).hexdigest(),
                      words=cert["words"])


def survey(max_length=10):
    bases = ["".join(pair) for pair in itertools.product("SKI", repeat=2)]
    bases += ["".join(triple) for triple in itertools.product("SK", repeat=3)]
    certificates, candidates = [], []
    for basis in bases:
        cert = certificate(basis, max_length)
        certificates.append(cert)
        if not cert["certified"]:
            continue
        for swapped, reverse in itertools.product((False, True), repeat=2):
            for shared in ((False, True) if reverse else (True,)):
                for optimize in (False, True):
                    _, report = measure(cert, swapped, reverse, shared, optimize)
                    candidates.append(report)
    candidates.sort(key=lambda row: (row["native_bits"], row["constants"], row["swapped"],
                                     row["reverse"], row["shared"], row["optimize"]))
    reference_files = ("functional.py", "bitfold.py")
    reference = b"".join(Path(__file__).with_name(name).read_bytes() for name in reference_files)
    return dict(max_word_length=max_length, normalization_budget=10000,
                contract="Separate program/input boolean-pair lists; bit-list output",
                reference_files=list(reference_files), reference_python_bytes=len(reference),
                reference_python_sha256=hashlib.sha256(reference).hexdigest(),
                certificates=certificates, candidates=candidates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", action="store_true")
    parser.add_argument("--max-length", type=int, default=10)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--run")
    parser.add_argument("--input", default="")
    parser.add_argument("--steps", type=int, default=1000000)
    args = parser.parse_args()
    if args.survey:
        report = survey(args.max_length)
        if not report["candidates"]:
            parser.error("word-search bound did not certify any candidates")
        best = report["candidates"][0]
        cert = next(c for c in report["certificates"] if c["constants"] == best["constants"])
        bits, _ = measure(cert, *(best[key] for key in ("swapped", "reverse", "shared", "optimize")))
        options = {key: best[key] for key in ("constants", "swapped", "reverse")}
    else:
        cert = certificate("SK", args.max_length)
        if not cert["certified"]:
            parser.error("word-search bound did not certify the baseline")
        bits, report = measure(cert)
        options = {}
    if args.run is not None:
        report["execution"] = read_bits(app(meaning(args.run, **options), bitlist(args.input)), budget=args.steps)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    if args.emit:
        args.emit.write_text(bits)
    if args.survey:
        summary = dict(certified=sum(c["certified"] for c in report["certificates"]),
                       candidates=len(report["candidates"]), best=report["candidates"][0])
        if args.run is not None:
            summary["execution"] = report["execution"]
        print(json.dumps(summary, indent=2))
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
