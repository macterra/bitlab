"""Binary triage-calculus experiment: one native operator, five local rules.

Rules follow Johannes Bader's triage variant of Barry Jay's tree calculus.
The machine uses lazy head reduction. All source strings are defined by a
prefix tree codec with virtual leaf completion at EOF. See TRIAGE.md.
"""

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from functional import app, named


T = "T"
K = app(T, T)
I = app(T, app(T, K), T)
S = app(T, app(T, app(K, T)), T)


def encode(term):
    pieces, pending = [], [term]
    while pending:
        node = pending.pop()
        if node == T:
            pieces.append("0")
        elif isinstance(node, tuple) and node[0] == "A":
            pieces.append("1")
            pending.extend((node[2], node[1]))
        else:
            raise ValueError("expected a closed triage expression")
    return "".join(pieces)


def parse(bits):
    """Read one tree; missing leaves are T, and complete-prefix suffixes remain."""
    if any(bit not in "01" for bit in bits):
        raise ValueError("expected bits")
    pending, position = [], 0
    while True:
        if position < len(bits) and bits[position] == "1":
            pending.append(None)
            position += 1
            continue
        if position < len(bits):
            position += 1
        value = T
        while pending and pending[-1] is not None:
            value = app(pending.pop(), value)
        if not pending:
            return value, bits[position:]
        pending[-1] = value


class Machine:
    """Resumable head reduction; demand frames inspect only native tree shapes."""
    def __init__(self, term):
        self.current, self.stack, self.frames, self.steps = term, [], [], 0

    @property
    def halted(self):
        return self.current == T and len(self.stack) < 3 and not self.frames

    def step(self):
        if self.halted:
            return False
        term = self.current
        if isinstance(term, tuple) and term[0] == "A":
            self.stack.append(term[2])
            self.current = term[1]
        elif term != T:
            raise ValueError("non-native term")
        elif len(self.stack) >= 3:
            first, second, third = self.stack.pop(), self.stack.pop(), self.stack.pop()
            self.frames.append(("first", second, third, self.stack))
            self.current, self.stack = first, []
        else:
            children = list(reversed(self.stack))
            frame = self.frames.pop()
            if frame[0] == "first":
                _, second, third, outer = frame
                if not children:  # T T y z -> y
                    self.current, self.stack = second, outer
                elif len(children) == 1:  # T (T x) y z -> x z (y z)
                    self.current = app(children[0], third, app(second, third))
                    self.stack = outer
                else:
                    self.frames.append(("third", children[0], children[1], second, outer))
                    self.current, self.stack = third, []
            else:
                _, leaf, stem, fork, outer = frame
                self.current = (leaf if not children else app(stem, children[0]) if len(children) == 1 else
                                app(fork, children[0], children[1]))
                self.stack = outer
        self.steps += 1
        return True

    def run(self, budget):
        if budget < 0:
            raise ValueError("negative budget")
        for _ in range(budget):
            if not self.step():
                break
        return "value" if self.halted else "suspended"

    def value(self):
        if not self.halted:
            raise ValueError("machine is suspended")
        return app(T, *reversed(self.stack))


def normalize(term, budget=1000000):
    remaining = budget

    def visit(node):
        nonlocal remaining
        machine = Machine(node)
        status = machine.run(remaining)
        remaining -= machine.steps + 1
        if status == "suspended" or remaining < 0:
            raise TimeoutError("normalization budget exhausted")
        return app(T, *(visit(child) for child in reversed(machine.stack)))

    return visit(term)


def compile_term(source):
    """Bracket abstraction into T; no eta rule and no hidden primitive S or K."""
    parsed = named("\\T. " + source)[1]

    def mark(node, depth=0):
        if isinstance(node, int):
            return T if node == depth else node
        if node[0] == "L":
            return ("L", mark(node[1], depth + 1))
        return app(mark(node[1], depth), mark(node[2], depth))

    @lru_cache(maxsize=None)
    def uses(node):
        if isinstance(node, int):
            return node == 0
        return False if node == T else uses(node[1]) or uses(node[2])

    def lower(node):
        if isinstance(node, int):
            return node - 1
        return T if node == T else app(lower(node[1]), lower(node[2]))

    def abstract(node):
        if not uses(node):
            return app(K, lower(node))
        if node == 0:
            return I
        left, right = node[1:]
        # S a b is exactly T (T a) b; expand directly instead of emitting S.
        return app(T, app(T, abstract(left)), abstract(right))

    def convert(node):
        if node == T or isinstance(node, int):
            return node
        if node[0] == "L":
            return abstract(convert(node[1]))
        return app(convert(node[1]), convert(node[2]))

    return convert(mark(parsed))


def quote(term):
    """Plain tree data: leaf T represents T; fork represents application."""
    return T if term == T else app(T, quote(term[1]), quote(term[2]))


def bitlist(bits):
    """Representation only. Nil=T; cons=T head tail; 0=T; 1=T T."""
    if any(bit not in "01" for bit in bits):
        raise ValueError("expected bits")
    result = T
    for bit in reversed(bits):
        result = app(T, T if bit == "0" else app(T, T), result)
    return result


def read_bits(term, budget=1000000, limit=100):
    remaining, output = budget, []

    def expose(value):
        nonlocal remaining
        machine = Machine(value)
        status = machine.run(remaining)
        remaining -= machine.steps
        if status == "suspended":
            raise TimeoutError
        return list(reversed(machine.stack))

    status = "limit"
    try:
        for _ in range(limit):
            fields = expose(term)
            if not fields:
                status = "end"
                break
            if len(fields) != 2:
                status = "non-list-value"
                break
            head, term = fields
            bit = expose(head)
            if bit and (len(bit) != 1 or expose(bit[0])):
                status = "non-bit-value"
                break
            output.append("1" if bit else "0")
    except TimeoutError:
        status = "suspended"
    return dict(output="".join(output), status=status, host_steps=budget - remaining)


@lru_cache(maxsize=1)
def structural_interpreter():
    # case q l s f = T (T l s) f q. Source input is a quoted syntax tree.
    return compile_term(r"""
        (\self. self self)
        (\self q. T (T T T) (\left right. self self left (self self right)) q)
    """)


@lru_cache(maxsize=1)
def binary_interpreter():
    # CPS parser, with nil supplying a virtual leaf and K discarding the suffix.
    return compile_term(r"""
        ((\self. self self)
         (\self continuation bits.
            T (T (continuation T T) T)
              (\head tail.
                T (T (continuation T tail)
                     (\ignored. self self
                       (\left. self self (\right. continuation (left right))) tail)) T head)
              bits))
        (T T)
    """)


def measure():
    structural, binary = structural_interpreter(), binary_interpreter()
    files = ["triage.py"]
    source = Path(__file__).read_bytes()
    return dict(runtime="Triage calculus, lazy head reduction; five native rewrite rules",
                binary_self_bits=len(encode(binary)), structural_self_bits=len(encode(structural)),
                structural_input="Quoted tree, not raw bits; host quote does not evaluate",
                binary_input="Separate raw program/input tree lists; prefix EOF supplies T",
                primitive_bits=dict(T=1, K=len(encode(K)), I=len(encode(I)), S=len(encode(S))),
                binary_sha256=hashlib.sha256(encode(binary).encode()).hexdigest(),
                structural_sha256=hashlib.sha256(encode(structural).encode()).hexdigest(),
                source_files=files, source_bytes=len(source), source_sha256=hashlib.sha256(source).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--emit-structural", type=Path)
    parser.add_argument("--run")
    parser.add_argument("--input", default="")
    parser.add_argument("--steps", type=int, default=1000000)
    args = parser.parse_args()
    report = measure()
    if args.run is not None:
        term, _ = parse(args.run)
        report["execution"] = read_bits(app(term, bitlist(args.input)), budget=args.steps)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    if args.emit:
        args.emit.write_text(encode(binary_interpreter()))
    if args.emit_structural:
        args.emit_structural.write_text(encode(structural_interpreter()))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
