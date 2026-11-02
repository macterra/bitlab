"""Co-design 24 binary lambda encodings and their native self-interpreters.

Only the source encoding and its decoder vary. The reference lambda machine,
boolean-pair lists, and separate program/input contract stay fixed.
"""

import argparse
import hashlib
import itertools
import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from functional import (IDENTITY, app, closed, contractions, encode as blc_encode,
                        lam, named)
from functional_candidates import parser_seed as original_parser_seed
from functional_rewrites import neighbors, replay


@dataclass(frozen=True)
class Encoding:
    abstraction: str
    application: str
    variable: str
    repeat: str

    def __post_init__(self):
        if (set((self.abstraction, self.application, self.variable)) not in
                ({"0", "10", "11"}, {"00", "01", "1"}) or self.repeat not in ("0", "1")):
            raise ValueError("expected a three-leaf binary prefix tree and a unary polarity")

    @property
    def stop(self):
        return "0" if self.repeat == "1" else "1"

    @property
    def key(self):
        return f"L{self.abstraction}-A{self.application}-V{self.variable}-U{self.repeat}"

    def encode(self, term):
        pieces, pending = [], [term]
        while pending:
            node = pending.pop()
            if isinstance(node, int) and node >= 0:
                pieces.append(self.variable + self.repeat * node + self.stop)
            elif isinstance(node, tuple) and node[0] == "L":
                pieces.append(self.abstraction)
                pending.append(node[1])
            elif isinstance(node, tuple) and node[0] == "A":
                pieces.append(self.application)
                pending.extend((node[2], node[1]))
            else:
                raise ValueError("not a lambda term")
        return "".join(pieces)

    def parse(self, bits):
        """Strict inspection utility; arbitrary-source meaning uses the decoder."""
        if any(bit not in "01" for bit in bits):
            raise ValueError("expected bits")
        position = 0
        tags = {self.abstraction: "L", self.application: "A", self.variable: "V"}

        def bit():
            nonlocal position
            if position == len(bits):
                raise ValueError("incomplete source")
            result = bits[position]
            position += 1
            return result

        def term():
            tag = bit()
            if tag not in tags:
                tag += bit()
            kind = tags[tag]
            if kind == "L":
                return lam(term())
            if kind == "A":
                return app(term(), term())
            index = 0
            while bit() == self.repeat:
                index += 1
            return index

        result = term()
        return result, bits[position:]

    def scorer(self):
        """Return a bounded memoized native-bit cost, not the BLC cost."""
        @lru_cache(maxsize=100000)
        def size(term):
            if isinstance(term, int):
                return len(self.variable) + term + 1
            if term[0] == "L":
                return len(self.abstraction) + size(term[1])
            return len(self.application) + size(term[1]) + size(term[2])
        return size


BASELINE = Encoding("00", "01", "1", "1")


def family():
    return [Encoding(*codes, repeat) for tree in (("00", "01", "1"), ("0", "10", "11"))
            for codes in itertools.permutations(tree) for repeat in ("1", "0")]


def parser_seed(encoding):
    """Generate a CPS parser; the original encoding exactly recovers Tromp's seed.

    Raw unary suffixes double as environment selectors. A shared recursive parse
    is factored when abstraction and application are siblings in the code tree.
    Neither technique is restricted to the baseline's tag or bit orientation.
    """
    if encoding.repeat == "1":
        cons = named(r"\head tail choose rest. choose head (rest tail)")
        skip = named(r"\bits. bits bits bits")
    else:
        cons = named(r"\head tail choose rest. choose (rest tail) head")
        skip = named(r"(\self. self self) (\self bits. bits (\choose rest. choose (self self rest) rest))")

    abstraction = r"(continuation (\environment argument. left (cons argument environment)))"
    application = r"(recursive (\right. continuation (\environment. left environment (right environment))))"
    leaf = {"L": rf"(recursive (\left. {abstraction}))",
            "A": rf"(recursive (\left. {application}))",
            "V": r"(\tail. continuation tail (skip tail))"}
    tags = {encoding.abstraction: "L", encoding.application: "A", encoding.variable: "V"}
    short = next(code for code in tags if len(code) == 1)
    long = "1" if short == "0" else "0"
    kinds = [tags[long + bit] for bit in "01"]
    if set(kinds) == {"L", "A"}:
        outcomes = {"L": abstraction, "A": application}
        next_handler = rf"(\second. recursive (\left. second {outcomes[kinds[0]]} {outcomes[kinds[1]]}))"
    else:
        next_handler = rf"(\second. second {leaf[kinds[0]]} {leaf[kinds[1]]})"
    short_handler = ("(continuation tail (skip tail))" if tags[short] == "V" else
                     f"({leaf[tags[short]]} tail)")
    branches = {short: short_handler, long: "(tail next)"}
    source = rf"""
        (\self. self self)
        (\self.
            (\recursive.
                (\continuation.
                    (\next. \bits.
                        bits (\first tail.
                            first {branches['0']} {branches['1']}))
                    {next_handler}))
            (self self))
    """
    return named(source, {"cons": cons, "skip": skip})


def decoder_seed(encoding):
    return app(parser_seed(encoding), IDENTITY)


def optimize(seed, encoding, *, mode="contract", rounds=12, beam=64, slack=128,
             max_generated=20000, progress=None):
    """Bounded native-cost search; certificates use BLC solely as a wire format."""
    if not closed(seed) or mode not in ("contract", "rewrite"):
        raise ValueError("expected a closed seed and supported search mode")
    if min(rounds, slack) < 0 or min(beam, max_generated) < 1:
        raise ValueError("invalid search bounds")
    size = encoding.scorer()
    best, best_proof = seed, []
    frontier, seen = [(seed, [])], {seed}
    generated, stopped, history = 0, False, []
    rules = {"contract": 0, "expand": 0, "join": 0}
    for round_number in range(1, rounds + 1):
        candidates = []
        for term, proof in frontier:
            if mode == "contract":
                changes = ((changed, dict(rule="contract", path=list(path)))
                           for path, changed in contractions(term))
            else:
                # Disable the old generator's BLC growth filter. The global
                # ceiling below is measured exclusively in this native encoding.
                changes = neighbors(term, max_growth=float("inf"))
            for changed, step in changes:
                if changed in seen:
                    continue
                seen.add(changed)
                generated += 1
                rules[step["rule"]] += 1
                stopped = generated >= max_generated
                length = size(changed)
                if length <= size(best) + slack:
                    trail = proof + [step]
                    candidates.append((length, encoding.encode(changed), changed, trail))
                    if length < size(best):
                        if replay(seed, trail) != changed:
                            raise ValueError("native search proof failed")
                        best, best_proof = changed, trail
                if stopped:
                    break
            if stopped:
                break
        candidates.sort(key=lambda row: (row[0], row[1]))
        frontier = [(term, proof) for length, _, term, proof in candidates[:beam]
                    if length <= size(best) + slack]
        row = dict(round=round_number, generated=generated, best_bits=size(best), retained=len(frontier))
        history.append(row)
        if progress:
            progress(row)
        if stopped or not frontier:
            break
    if replay(seed, best_proof) != best:
        raise ValueError("final native search proof failed")
    report = dict(mode=mode, rounds=rounds, beam=beam, slack=slack, max_generated=max_generated,
                  seed_bits=size(seed), result_bits=size(best), generated=generated, rules=rules,
                  stop_reason="candidate limit" if stopped else ("empty frontier" if not frontier else "round limit"),
                  history=history, proof=best_proof)
    size.cache_clear()
    return best, report


def measure(encoding, rewrite=True):
    seed = decoder_seed(encoding)
    kernel, reduction = optimize(seed, encoding)
    phases = [reduction]
    proof = reduction["proof"]
    if rewrite:
        kernel, rewriting = optimize(kernel, encoding, mode="rewrite", rounds=6,
                                      beam=32, slack=32, max_generated=30000)
        phases.append(rewriting)
        proof = proof + rewriting["proof"]
    if replay(seed, proof) != kernel:
        raise ValueError("combined proof failed")
    bits = encoding.encode(kernel)
    return kernel, dict(key=encoding.key, encoding=asdict(encoding), seed_bits=len(encoding.encode(seed)),
                        native_bits=len(bits), blc_bits=len(blc_encode(kernel)),
                        sha256=hashlib.sha256(bits.encode()).hexdigest(), artifact=bits,
                        phases=phases, proof=proof)


def survey(rewrite=True, progress=None):
    if parser_seed(BASELINE) != original_parser_seed():
        raise ValueError("generator failed to reproduce the original parser seed")
    rows = []
    for encoding in family():
        _, row = measure(encoding, rewrite)
        rows.append(row)
        if progress:
            progress(dict(key=row["key"], seed_bits=row["seed_bits"], native_bits=row["native_bits"],
                          generated=sum(phase["generated"] for phase in row["phases"])))
    rows.sort(key=lambda row: (row["native_bits"], row["key"]))
    calibration = next(row for row in rows if row["key"] == BASELINE.key)
    if calibration["native_bits"] > 174:
        raise ValueError("search failed to recover the 174-bit calibration")
    files = ["functional.py", "functional_candidates.py", "functional_rewrites.py", "encoding_search.py"]
    source = b"".join(Path(__file__).with_name(name).read_bytes() for name in files)
    return dict(contract="Separate raw program/input boolean-pair lists; bit-list output",
                variants=len(rows), rewrite=rewrite, best_key=rows[0]["key"], best_bits=rows[0]["native_bits"],
                generated_across_variants=sum(phase["generated"] for row in rows for phase in row["phases"]),
                proof_encoding="Standard BLC for certificate replacements only; native sizes use each row's encoding",
                source_files=files, source_bytes=len(source), source_sha256=hashlib.sha256(source).hexdigest(),
                candidates=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-rewrite", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--emit", type=Path)
    args = parser.parse_args()
    report = survey(not args.no_rewrite, progress=lambda row: print(json.dumps(row), flush=True))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    if args.emit:
        args.emit.write_text(report["candidates"][0]["artifact"])
    print(json.dumps({key: value for key, value in report.items() if key != "candidates"}, indent=2))


if __name__ == "__main__":
    main()
