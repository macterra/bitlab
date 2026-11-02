"""Compare both scan directions with the same bitfold optimization budgets."""

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from bitfold import CONSTANTS, certificate, compile_sk, interpreter, native_encode
from functional import encode, named
from functional_candidates import search
from functional_rewrites import replay, search as rewrite_search
from reflective_fold import build, reflection_seed


def forward_seed(basis="SK"):
    return named(r"((\s. s s) (\s acc bits. bits "
                 r"(\bit tail ignored. s s (bit (acc " + " ".join(basis) +
                 r") (S (K acc))) tail) acc)) I", CONSTANTS)


@lru_cache(maxsize=2)
def forward(basis="SK"):
    original = interpreter(constants=basis, reverse=False, shared=True)
    seed = forward_seed(basis)
    bridge = dict(rule="join", path=[], replacement=encode(seed),
                  before=[[1], [1, 1, 1], [1, 2, 1]], after=[[1]])
    if replay(original, [bridge]) != seed:
        raise ValueError("forward fixed-point restructuring failed")
    base, reduction = search(seed, rounds=16, beam=128, slack=100)
    proof = [bridge] + [dict(rule="contract", path=list(path)) for path in reduction["beta_paths"]]
    base, polishing = rewrite_search(base, rounds=2, beam=64, slack=32, max_generated=20000)
    proof += polishing["proof"]
    if replay(original, proof) != base:
        raise ValueError("forward fold kernel proof failed")
    reflected, reflection_reduction = search(reflection_seed(base), rounds=16, beam=128, slack=100)
    reflection_proof = [dict(rule="contract", path=list(path))
                        for path in reflection_reduction["beta_paths"]]
    if replay(reflection_seed(base), reflection_proof) != reflected:
        raise ValueError("forward reflection proof failed")
    cert = certificate(basis)
    native = native_encode(compile_sk(base, cert["words"]), cert["words"], reverse=False)
    report = dict(basis=basis, scan="left-to-right", ordinary_kernel_bits=len(encode(base)),
                  ordinary_self_bits=len(native), reflective_kernel_bits=len(encode(reflected)),
                  reflective_self_bits=0, original_kernel_bits=len(encode(original)),
                  kernel_blc=encode(base), reflective_kernel_blc=encode(reflected),
                  ordinary_self_program=native, certificate=cert, proof=proof,
                  reflection_proof=reflection_proof, reduction=reduction,
                  kernel_rewrite=polishing, reflection_reduction=reflection_reduction,
                  ordinary_kernel_sha256=hashlib.sha256(encode(base).encode()).hexdigest(),
                  reflective_kernel_sha256=hashlib.sha256(encode(reflected).encode()).hexdigest(),
                  ordinary_self_sha256=hashlib.sha256(native.encode()).hexdigest())
    return base, reflected, report


def survey():
    rows = [candidate(basis)[2] for basis in ("SK", "KSK") for candidate in (forward, build)]
    files = ["functional.py", "functional_candidates.py", "functional_rewrites.py",
             "bitfold.py", "reflective_fold.py", "direction_search.py"]
    source = b"".join(Path(__file__).with_name(name).read_bytes() for name in files)
    return dict(contract="Unchanged separate raw program/input boolean-pair lists; bit-list output",
                method="Direct self-application seeds; identical contraction, rewrite, and reflection budgets",
                source_files=files, source_bytes=len(source), source_sha256=hashlib.sha256(source).hexdigest(),
                candidates=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = survey()
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    keys = ("basis", "scan", "ordinary_kernel_bits", "ordinary_self_bits", "reflective_kernel_bits")
    print(json.dumps([{key: row[key] for key in keys} for row in report["candidates"]], indent=2))


if __name__ == "__main__":
    main()
