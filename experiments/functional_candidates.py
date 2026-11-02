"""Functional language candidates and a reproducible local reduction search.

The parser below reconstructs Tromp's 168-bit intL mathematically, with credit to
50_ft_lock and Sean Palmer for the optimized construction. See FUNCTIONAL.md.
No novelty or minimality is claimed for that calibration term.
"""

from core.artifacts import ROOT, repo_path

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from core.lambda_calculus import IDENTITY, NIL, Machine, app, bitlist, closed, contractions, encode, named, read_bits


from core.search import search


def parser_seed():
    # cons supports lookup directly by a unary variable-index bitstream.
    cons = named(r"\head tail choose rest. choose head (rest tail)")
    skip = named(r"\bits. bits bits bits")
    return named(r"""
        (\self. self self)
        (\self.
            (\recursive.
                (\continuation.
                    (\next. \bits.
                        bits (\first tail.
                            first (tail next) (continuation tail (skip tail))))
                    (\second.
                        recursive (\left.
                            second
                                (continuation (\environment argument.
                                    left (cons argument environment)))
                                (recursive (\right.
                                    continuation (\environment.
                                        left environment (right environment))))))))
            (self self))
    """, {"cons": cons, "skip": skip})


@lru_cache(maxsize=1)
def tromp_parser():
    term, _ = search(parser_seed(), rounds=20, beam=256, slack=150)
    return term


@lru_cache(maxsize=1)
def decoder():
    """D p returns the decoded closed term, when p has a valid closed prefix.

    For every other bitstring, D (bitlist p) is still a closed lambda computation.
    Its behavior, rather than an external repair rule, defines the total language.
    The identity continuation uses the unused suffix as the binding environment.
    Closed source terms do not inspect that environment.
    """
    return app(tromp_parser(), IDENTITY)


def program(bits, argument=NIL, kernel=None):
    """Every finite source bitstring denotes this closed functional computation."""
    return app(decoder() if kernel is None else kernel, bitlist(bits), argument)



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--beam", type=int, default=256)
    parser.add_argument("--slack", type=int, default=400)
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--run", help="raw source bits")
    parser.add_argument("--input", default="", help="external input as a bit list")
    parser.add_argument("--output-limit", type=int, default=100)
    parser.add_argument("--steps", type=int, default=100000)
    args = parser.parse_args()
    kernel = decoder()
    report = {"tromp_parser_bits": len(encode(tromp_parser())),
              "seed_decoder_bits": len(encode(kernel))}
    if args.search:
        kernel, report["search"] = search(kernel, args.rounds, args.beam, args.slack)
    bits = encode(kernel)
    reference = repo_path("core/lambda_calculus.py").read_bytes()
    report.update(bits=len(bits), closed=closed(kernel),
                  sha256=hashlib.sha256(bits.encode("ascii")).hexdigest(),
                  reference_python_bytes=len(reference),
                  reference_python_sha256=hashlib.sha256(reference).hexdigest(),
                  provenance="https://github.com/tromp/AIT/blob/2cfa384f11d462e77dfe96d3c5fefbecfa7ff432/ait/int.lam")
    if args.emit:
        args.emit.write_text(bits, encoding="ascii")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.run is not None:
        report.update(read_bits(program(args.run, bitlist(args.input), kernel=kernel),
                                budget=args.steps, limit=args.output_limit))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
