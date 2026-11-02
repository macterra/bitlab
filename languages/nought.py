"""Smaller bitfold kernels and explicit empty-program self-interpretation.

The ordinary folds preserve the earlier SK/KSK reverse-scan languages exactly.
The reflective variants change only empty source to denote their own decoder.
Both use the existing raw boolean-pair list interface and lambda machine.
"""

from core.artifacts import source_files, source_bytes

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from core.combinators import CONSTANTS, compile_sk
from languages.bitfold import certificate, interpreter, native_encode
from core.lambda_calculus import app, bitlist, encode, named, read_bits
from core.search import search
from core.rewrites import replay, search as rewrite_search


def fold_seed(basis="SK"):
    return named(r"(\s. s s) (\s bits. bits (\bit tail ignored. (\acc. bit (acc " +
                 " ".join(basis) + r") (S (K acc))) (s s tail)) I)", CONSTANTS)


from core.reflection import reflection_seed

@lru_cache(maxsize=2)
def build(basis="SK"):
    original = interpreter(constants=basis, reverse=True, shared=True)
    seed = fold_seed(basis)
    # Both fixed-point presentations beta-reduce to the same explicit A A.
    bridge = dict(rule="join", path=[], replacement=encode(seed),
                  before=[[], [1, 1], [2, 1]], after=[[]])
    if replay(original, [bridge]) != seed:
        raise ValueError("fixed-point restructuring failed")
    base, reduction = search(seed, rounds=16, beam=128, slack=100)
    proof = [bridge] + [dict(rule="contract", path=list(path)) for path in reduction["beta_paths"]]
    base, polishing = rewrite_search(base, rounds=2, beam=64, slack=32, max_generated=20000)
    proof += polishing["proof"]
    if replay(original, proof) != base:
        raise ValueError("fold kernel proof failed")
    reflected, reflection_reduction = search(reflection_seed(base), rounds=16, beam=128, slack=100)
    reflection_proof = [dict(rule="contract", path=list(path)) for path in reflection_reduction["beta_paths"]]
    if replay(reflection_seed(base), reflection_proof) != reflected:
        raise ValueError("reflection kernel proof failed")
    cert = certificate(basis)
    native = native_encode(compile_sk(base, cert["words"]), cert["words"], reverse=True)
    report = dict(basis=basis, scan="right-to-left", ordinary_kernel_bits=len(encode(base)),
                  ordinary_self_bits=len(native), reflective_kernel_bits=len(encode(reflected)),
                  reflective_self_bits=0, original_kernel_bits=len(encode(original)),
                  kernel_blc=encode(base), reflective_kernel_blc=encode(reflected),
                  ordinary_self_program=native, certificate=cert, proof=proof,
                  reflection_proof=reflection_proof, reduction=reduction,
                  kernel_rewrite=polishing,
                  reflection_reduction=reflection_reduction,
                  ordinary_kernel_sha256=hashlib.sha256(encode(base).encode()).hexdigest(),
                  reflective_kernel_sha256=hashlib.sha256(encode(reflected).encode()).hexdigest(),
                  ordinary_self_sha256=hashlib.sha256(native.encode()).hexdigest())
    return base, reflected, report


def survey():
    rows = [build(basis)[2] for basis in ("SK", "KSK")]
    rows.sort(key=lambda row: (row["reflective_kernel_bits"], row["basis"]))
    files = source_files(__file__)
    source = source_bytes(files)
    return dict(contract="Unchanged separate raw program/input boolean-pair lists; bit-list output",
                best_basis=rows[0]["basis"], best_self_bits=0, best_kernel_bits=rows[0]["reflective_kernel_bits"],
                source_files=files, source_bytes=len(source), source_sha256=hashlib.sha256(source).hexdigest(),
                candidates=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--kernel", type=Path)
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--run")
    parser.add_argument("--input", default="")
    parser.add_argument("--steps", type=int, default=1000000)
    args = parser.parse_args()
    report = survey()
    if args.kernel:
        args.kernel.write_text(report["candidates"][0]["reflective_kernel_blc"])
    if args.emit:
        args.emit.write_text("")
    if args.run is not None:
        _, kernel, _ = build(report["best_basis"])
        report["execution"] = read_bits(app(kernel, bitlist(args.run), bitlist(args.input)), budget=args.steps)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    summary = {key: value for key, value in report.items() if key != "candidates"}
    summary["sizes"] = [{key: row[key] for key in ("basis", "ordinary_kernel_bits", "ordinary_self_bits",
                                                   "reflective_kernel_bits", "reflective_self_bits")}
                        for row in report["candidates"]]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
