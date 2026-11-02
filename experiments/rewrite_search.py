"""Reproduce the functional decoder equivalence-search experiment."""

from core.artifacts import source_files, source_bytes

import argparse
import hashlib
import json
from pathlib import Path
from core.lambda_calculus import IDENTITY, app, contract_at, encode
from core.rewrites import at, search
from core.search import search as contraction_search
from experiments.functional_candidates import decoder, parser_seed


def source_proof():
    """Reverse the existing calibration to recover the 193-bit source decoder."""
    _, calibration = contraction_search(parser_seed(), slack=150)
    term = app(parser_seed(), IDENTITY)
    reverse = []
    for local_path in calibration["beta_paths"]:
        path = [1, *local_path]
        reverse.append(dict(rule="expand", path=path, replacement=encode(at(term, path))))
        term = contract_at(term, path)
    if term != decoder():
        raise ValueError("calibration does not lead to the baseline decoder")
    return list(reversed(reverse))



def suite(progress=None):
    """Three fixed, reproducible searches; counts overlap between runs."""
    settings = [dict(rounds=12, beam=64, slack=32),
                dict(rounds=16, beam=64, slack=192, policy="layers", subsets=True,
                     max_generated=300000),
                dict(rounds=16, beam=128, slack=64, policy="layers", subsets=True,
                     max_generated=500000, start_proofs=[source_proof()])]
    runs, best, best_report = [], decoder(), None
    for index, options in enumerate(settings, 1):
        callback = (lambda row, index=index: progress(dict(row, run=index))) if progress else None
        term, report = search(decoder(), **options, progress=callback)
        runs.append(report)
        if best_report is None or size(term) < size(best):
            best, best_report = term, report
    report = dict(best_report, runs=runs,
                  generated_across_runs=sum(row["generated"] for row in runs))
    return best, report



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--beam", type=int, default=64)
    parser.add_argument("--slack", type=int, default=32)
    parser.add_argument("--subsets", action="store_true")
    parser.add_argument("--policy", choices=("size", "layers"), default="size")
    parser.add_argument("--max-generated", type=int, default=500000)
    parser.add_argument("--source-start", action="store_true")
    parser.add_argument("--suite", action="store_true", help="run the fixed three-profile experiment")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--emit", type=Path)
    args = parser.parse_args()
    progress = lambda row: print(json.dumps(row), flush=True)
    if args.suite:
        best, report = suite(progress)
    else:
        best, report = search(decoder(), args.rounds, args.beam, args.slack, args.subsets,
                              args.policy, args.max_generated,
                              [source_proof()] if args.source_start else [], progress)
    files = source_files(__file__)
    source = source_bytes(files)
    report.update(search_files=files, search_source_sha256=hashlib.sha256(source).hexdigest(),
                  search_source_bytes=len(source))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    if args.emit:
        args.emit.write_text(encode(best))
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("history", "proof", "start_proofs", "runs")}, indent=2))



if __name__ == "__main__":
    main()
