"""Bounded BLC size search with replayable beta-equivalence certificates.

Search heuristics are untrusted: replay checks every step using capture-avoiding
beta contraction from functional.py. No eta rules or new guest primitives.
"""

import argparse
import hashlib
import itertools
import json
from functools import lru_cache
from pathlib import Path

from functional import IDENTITY, app, beta, closed, contract_at, encode, lam, parse, shift
from functional_candidates import decoder, parser_seed, search as contraction_search


@lru_cache(maxsize=100000)
def size(term):
    if isinstance(term, int):
        return term + 2
    return 2 + size(term[1]) + (size(term[2]) if term[0] == "A" else 0)


def positions(term, path=(), depth=0):
    yield path, term, depth
    if isinstance(term, int):
        return
    yield from positions(term[1], path + (1,), depth + (term[0] == "L"))
    if term[0] == "A":
        yield from positions(term[2], path + (2,), depth)


def at(term, path):
    for index in path:
        if isinstance(term, int) or index not in ((1,) if term[0] == "L" else (1, 2)):
            raise ValueError("invalid term path")
        term = term[index]
    return term


def replace(term, path, value):
    if not path:
        return value
    at(term, path)  # Validate before changing the tree.
    children = list(term)
    children[path[0]] = replace(children[path[0]], path[1:], value)
    return tuple(children)


def outward(term, count, cutoff=0):
    """Move a subterm across count binders, rejecting references they bind."""
    if isinstance(term, int):
        if cutoff <= term < cutoff + count:
            raise ValueError("subterm depends on an intervening binder")
        return term - count if term >= cutoff + count else term
    if term[0] == "L":
        return lam(outward(term[1], count, cutoff + 1))
    return app(outward(term[1], count, cutoff), outward(term[2], count, cutoff))


def extract(term, argument, paths):
    """Inverse beta: replace selected occurrences by a fresh helper binding."""
    selected = set(paths)

    def body(node, path=(), depth=0):
        if path in selected:
            if node != shift(argument, depth):
                raise ValueError("extraction would capture a variable")
            return depth
        if isinstance(node, int):
            return node + (node >= depth)
        if node[0] == "L":
            return lam(body(node[1], path + (1,), depth + 1))
        return app(body(node[1], path + (1,), depth), body(node[2], path + (2,), depth))

    result = app(lam(body(term)), argument)
    if beta(result[1][1], result[2]) != term:
        raise ValueError("invalid inverse beta step")
    return result


def exchange(term, depth=0):
    """Exchange the two nearest surrounding binders, under arbitrary lambdas."""
    if isinstance(term, int):
        if term == depth:
            return depth + 1
        return depth if term == depth + 1 else term
    if term[0] == "L":
        return lam(exchange(term[1], depth + 1))
    return app(exchange(term[1], depth), exchange(term[2], depth))


def local_rewrites(term, max_growth=32, subsets=False):
    """Contraction, helper extraction, and adjacent applied-binder exchange.

    Helpers may be open in the current scope, but cannot depend on binders
    between the extraction site and the occurrence. Extract all occurrences,
    or one; optionally every nonempty subset when there are at most 6.
    """
    if isinstance(term, int):
        return
    if term[0] == "A" and isinstance(term[1], tuple) and term[1][0] == "L":
        yield beta(term[1][1], term[2]), {"rule": "contract"}

    # ((lambda x y. body) a) b, with both arguments exchanged as well.
    if term[0] == "A" and isinstance(term[1], tuple) and term[1][0] == "A":
        function, first = term[1][1:]
        if (isinstance(function, tuple) and function[0] == "L" and
                isinstance(function[1], tuple) and function[1][0] == "L"):
            changed = app(lam(lam(exchange(function[1][1]))), term[2], first)
            if changed != term:
                yield changed, {"rule": "join", "replacement": encode(changed),
                                "before": [[1], []], "after": [[1], []]}

    occurrences = {}
    for path, node, depth in positions(term):
        if not path:  # Exclude the trivial identity wrapper around the whole term.
            continue
        try:
            argument = outward(node, depth)
        except ValueError:
            continue
        occurrences.setdefault(argument, []).append(path)
    for argument, paths in occurrences.items():
        selections = [paths] + [[path] for path in paths] if len(paths) > 1 else [paths]
        if subsets and 2 < len(paths) <= 6:
            selections += [list(group) for count in range(2, len(paths))
                           for group in itertools.combinations(paths, count)]
        seen = set()
        for selected in selections:
            changed = extract(term, argument, selected)
            if changed in seen or size(changed) > size(term) + max_growth:
                continue
            seen.add(changed)
            yield changed, {"rule": "expand", "replacement": encode(changed)}


def neighbors(term, max_growth=32, subsets=False):
    seen = set()
    for path, node, _ in positions(term):
        for changed, proof in local_rewrites(node, max_growth, subsets):
            result = replace(term, path, changed)
            if result == term or result in seen:
                continue
            seen.add(result)
            yield result, dict(proof, path=list(path))


def replay(seed, proof):
    """Check a proof without invoking any of the candidate-generation code.

    Each expansion must contract back exactly. Other bidirectional rewrites
    must supply a common beta reduct. All whole-program terms remain closed.
    """
    if not closed(seed):
        raise ValueError("proof seed must be closed")
    term = seed
    for step in proof:
        path = step["path"]
        original = at(term, path)
        rule = step["rule"]
        if rule == "contract":
            changed = contract_at(original, ())
        elif rule in ("expand", "join"):
            changed, suffix = parse(step["replacement"])
            if suffix:
                raise ValueError("replacement has ignored suffix")
            if rule == "expand":
                if contract_at(changed, ()) != original:
                    raise ValueError("expansion does not contract to the original")
            else:
                before, after = original, changed
                for reduction in step["before"]:
                    before = contract_at(before, reduction)
                for reduction in step["after"]:
                    after = contract_at(after, reduction)
                if before != after:
                    raise ValueError("rewrites have no certified common reduct")
        else:
            raise ValueError("unknown proof rule")
        term = replace(term, path, changed)
        if not closed(term):
            raise ValueError("rewrite created an unbound variable")
    return term


def choose(candidates, beam, policy):
    """Keep the shortest terms, or share the beam across occupied size layers."""
    candidates.sort(key=lambda item: (item[0], item[1]))
    if policy == "size":
        return candidates[:beam]
    groups = [list(group) for _, group in itertools.groupby(candidates, key=lambda item: item[0])]
    result = []
    for rank in range(beam):
        for group in groups:
            if rank < len(group):
                result.append(group[rank])
                if len(result) == beam:
                    return result
        if all(rank >= len(group) for group in groups):
            break
    return result


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


def search(seed, rounds=12, beam=64, slack=32, subsets=False, policy="size",
           max_generated=500000, start_proofs=(), progress=None):
    """Deterministic bounded beam search; absence of improvement proves no bound."""
    if (not closed(seed) or min(rounds, slack) < 0 or beam < 1 or
            policy not in ("size", "layers") or max_generated < 1):
        raise ValueError("expected closed seed, nonnegative bounds, and positive beam")
    best, best_proof = seed, []
    frontier = [(seed, [])]
    seen = {seed}
    for proof in start_proofs:
        initial = replay(seed, proof)
        if size(initial) > size(seed) + slack:
            raise ValueError("additional search start exceeds the size bound")
        if initial not in seen:
            seen.add(initial)
            frontier.append((initial, proof))
        if size(initial) < size(best):
            best, best_proof = initial, proof
    history, generated, exhausted = [], 0, False
    rules = {"contract": 0, "expand": 0, "join": 0}
    for round_number in range(1, rounds + 1):
        candidates = []
        for term, proof in frontier:
            for changed, step in neighbors(term, slack, subsets):
                if changed in seen:
                    continue
                seen.add(changed)
                generated += 1
                rules[step["rule"]] += 1
                if generated >= max_generated:
                    exhausted = True
                if size(changed) > size(best) + slack:
                    if exhausted:
                        break
                    continue
                trail = proof + [step]
                candidates.append((size(changed), encode(changed), changed, trail))
                if size(changed) < size(best):
                    replayed = replay(seed, trail)
                    if replayed != changed:
                        raise ValueError("search proof failed to replay")
                    best, best_proof = changed, trail
                if exhausted:
                    break
            if exhausted:
                break
        candidates = [item for item in candidates if item[0] <= size(best) + slack]
        frontier = [(term, proof) for _, _, term, proof in choose(candidates, beam, policy)]
        lengths = [size(term) for term, _ in frontier]
        row = dict(round=round_number, generated=generated, retained=len(frontier),
                   best_bits=size(best), frontier_min=min(lengths) if lengths else None,
                   frontier_max=max(lengths) if lengths else None)
        history.append(row)
        if progress:
            progress(row)
        if exhausted or not frontier:
            break
    if replay(seed, best_proof) != best:
        raise ValueError("final proof failed")
    bits = encode(best)
    report = dict(seed_bits=size(seed), result_bits=len(bits), rounds=rounds, beam=beam,
                  slack=slack, subsets=subsets, policy=policy, max_generated=max_generated,
                  start_proofs=list(start_proofs),
                  stop_reason="candidate limit" if exhausted else ("empty frontier" if not frontier else "round limit"),
                  generated=generated, rules=rules,
                  history=history, proof=best_proof,
                  seed_sha256=hashlib.sha256(encode(seed).encode()).hexdigest(),
                  sha256=hashlib.sha256(bits.encode()).hexdigest())
    return best, report


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
    files = ["functional.py", "functional_candidates.py", "functional_rewrites.py"]
    source = b"".join(Path(__file__).with_name(name).read_bytes() for name in files)
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
