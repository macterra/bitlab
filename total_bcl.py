"""Totalized BCL with EOF completion and optional empty-source reflection.

00 = K, 01 = S, 1 <function> <argument> = application. Missing terms or
missing atom selector bits default to K. Bits after the first term are unused.
The reflective variant reserves empty source for its own decoder.
"""

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from bitfold import K, S, compile_sk
from functional import NIL, app, bitlist, encode, named, read_bits
from functional_candidates import search
from functional_rewrites import replay, search as rewrite_search
from reflective_fold import reflection_seed


def native_encode(tree):
    parts, pending = [], [tree]
    while pending:
        node = pending.pop()
        if node == "K":
            parts.append("00")
        elif node == "S":
            parts.append("01")
        elif isinstance(node, tuple) and node[0] == "A":
            parts.append("1")
            pending.extend((node[2], node[1]))
        else:
            raise ValueError("expected a closed SK tree")
    return "".join(parts)


def compile_program(term):
    return native_encode(compile_sk(term, {"K": "00", "S": "01"}))


def seed():
    # The parser returns the decoded term and remaining source to its continuation.
    # Both EOF cases are explicit lambda branches, not host repairs to the input.
    return named(r"""((\s. s s) (\s k bits.
        bits (\first tail ignored.
            first
                (tail (\second rest ignored. k (second K S) rest) (k K nil))
                (s s (\f rest. s s (\x rest. k (f x) rest) rest) tail))
            (k K nil))) (\value rest. value)""", {"K": K, "S": S, "nil": NIL})


@lru_cache(maxsize=1)
def build():
    base, reduction = search(seed(), rounds=16, beam=128, slack=100)
    proof = [dict(rule="contract", path=list(path)) for path in reduction["beta_paths"]]
    base, rewriting = rewrite_search(base, rounds=2, beam=64, slack=32, max_generated=20000)
    proof += rewriting["proof"]
    if replay(seed(), proof) != base:
        raise ValueError("invalid decoder proof")
    reflected, reflection_reduction = search(reflection_seed(base), rounds=16, beam=128, slack=100)
    reflection_proof = [dict(rule="contract", path=list(path))
                        for path in reflection_reduction["beta_paths"]]
    if replay(reflection_seed(base), reflection_proof) != reflected:
        raise ValueError("invalid reflection proof")
    ordinary_self = compile_program(base)
    report = dict(ordinary_kernel_bits=len(encode(base)),
                  reflective_kernel_bits=len(encode(reflected)),
                  ordinary_self_bits=len(ordinary_self), reflective_self_bits=0,
                  kernel_blc=encode(base), reflective_kernel_blc=encode(reflected),
                  ordinary_self_program=ordinary_self,
                  reduction=reduction, kernel_rewrite=rewriting, proof=proof,
                  reflection_reduction=reflection_reduction, reflection_proof=reflection_proof)
    for field in ("kernel_blc", "reflective_kernel_blc", "ordinary_self_program"):
        report[field + "_sha256"] = hashlib.sha256(report[field].encode()).hexdigest()
    return base, reflected, report


def report():
    from rule30 import step_function

    result = dict(build()[2])
    result["rule30_program"] = compile_program(step_function())
    result["rule30_bits"] = len(result["rule30_program"])
    result["contract"] = "Separate raw program/input boolean-pair lists; EOF defaults to K; suffix unused; empty source reflects"
    files = ["functional.py", "functional_candidates.py", "functional_rewrites.py", "bitfold.py",
             "reflective_fold.py", "total_bcl.py", "rule30.py"]
    source = b"".join(Path(__file__).with_name(name).read_bytes() for name in files)
    result.update(source_files=files, source_bytes=len(source), source_sha256=hashlib.sha256(source).hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--kernel", type=Path)
    parser.add_argument("--emit", type=Path, help="write the empty native self-interpreter")
    parser.add_argument("--rule30", type=Path, help="write the compiled Rule 30 program")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--run", help="raw source bits")
    source.add_argument("--run-file", type=Path, help="file containing raw source bits")
    parser.add_argument("--input", default="")
    parser.add_argument("--steps", type=int, default=20000000)
    parser.add_argument("--output-limit", type=int, default=100)
    args = parser.parse_args()
    result = report()
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    if args.kernel:
        args.kernel.write_text(result["reflective_kernel_blc"])
    if args.emit:
        args.emit.write_text("")
    if args.rule30:
        args.rule30.write_text(result["rule30_program"])
    summary = {key: result[key] for key in ("ordinary_kernel_bits", "reflective_kernel_bits",
                                           "ordinary_self_bits", "reflective_self_bits", "rule30_bits")}
    program = args.run_file.read_text() if args.run_file else args.run
    if program is not None:
        summary["execution"] = read_bits(app(build()[1], bitlist(program), bitlist(args.input)),
                                         budget=args.steps, limit=args.output_limit)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
