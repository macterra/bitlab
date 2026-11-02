"""Small lambda-calculus research kernel; zero-based de Bruijn indices.

Terms are integers (bound variables), ('L', body), or ('A', function, argument).
Strings are optional observation probes, never program instructions.
"""

import re
from dataclasses import dataclass


def lam(body):
    return ("L", body)


def app(*terms):
    result = terms[0]
    for argument in terms[1:]:
        result = ("A", result, argument)
    return result


def named(source, definitions=None):
    """Development notation: backslash binders, application, and parentheses.

    Named definitions must be closed terms; they are expanded before measuring.
    This compiler is not used to interpret binary guest programs.
    """
    definitions = definitions or {}
    tokens = re.findall(r"[A-Za-z_][A-Za-z_0-9']*|[\\.()]|\S", source)
    pos = 0

    def expression(scope):
        nonlocal pos
        terms = []
        while pos < len(tokens) and tokens[pos] != ")":
            token = tokens[pos]
            pos += 1
            if token == "\\":
                names = []
                while pos < len(tokens) and tokens[pos] != ".":
                    name = tokens[pos]
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9']*", name):
                        raise ValueError("invalid binder")
                    names.append(name)
                    pos += 1
                if not names or pos == len(tokens):
                    raise ValueError("expected binders followed by a dot")
                pos += 1
                term = expression(tuple(reversed(names)) + scope)
                for _ in names:
                    term = lam(term)
                terms.append(term)
                break
            if token == "(":
                term = expression(scope)
                if pos == len(tokens) or tokens[pos] != ")":
                    raise ValueError("missing closing parenthesis")
                pos += 1
            elif token in scope:
                term = scope.index(token)
            elif token in definitions:
                term = definitions[token]
                if not closed(term):
                    raise ValueError("definitions must be closed")
            else:
                raise ValueError(f"unknown identifier: {token}")
            terms.append(term)
        if not terms:
            raise ValueError("empty expression")
        return app(*terms)

    term = expression(())
    if pos != len(tokens):
        raise ValueError("unexpected closing parenthesis")
    return term


def closed(term, depth=0):
    if isinstance(term, int):
        return 0 <= term < depth
    if isinstance(term, str):
        return False
    if term[0] == "L":
        return closed(term[1], depth + 1)
    return closed(term[1], depth) and closed(term[2], depth)


def encode(term):
    """Standard BLC serialization; not a definition of arbitrary-source semantics."""
    pieces, pending = [], [term]
    while pending:
        node = pending.pop()
        if isinstance(node, int) and node >= 0:
            pieces.append("1" * (node + 1) + "0")
        elif isinstance(node, tuple) and node[0] == "L":
            pieces.append("00")
            pending.append(node[1])
        elif isinstance(node, tuple) and node[0] == "A":
            pieces.append("01")
            pending.extend((node[2], node[1]))
        else:
            raise ValueError("not a lambda term")
    return "".join(pieces)


def parse(bits):
    """Strict BLC inspection utility: one term and its unconsumed suffix.

    Used for calibration and valid-term comparisons, never as the total language
    frontend. An incomplete BLC term is an error in this inspection utility only.
    """
    if any(bit not in "01" for bit in bits):
        raise ValueError("expected bits")
    pos = 0

    def bit():
        nonlocal pos
        if pos == len(bits):
            raise ValueError("incomplete BLC term")
        value = bits[pos]
        pos += 1
        return value

    def term():
        if bit() == "1":
            index = 0
            while bit() == "1":
                index += 1
            return index
        if bit() == "0":
            return lam(term())
        return app(term(), term())

    result = term()
    return result, bits[pos:]


@dataclass(frozen=True)
class Closure:
    term: object
    environment: tuple = ()


class Machine:
    """Call-by-name Krivine machine, with resumable host-step budgets.

    All environment lookup, application, and binding steps are explicit. Source
    languages supply closed lambda terms, so no variable can be unbound at run
    time. A result is a weak-head value, not necessarily a full normal form.
    """
    def __init__(self, term, arguments=()):
        self.current = term if isinstance(term, Closure) else Closure(term)
        self.stack = [a if isinstance(a, Closure) else Closure(a)
                      for a in reversed(arguments)]
        self.steps = 0

    @property
    def halted(self):
        term = self.current.term
        return isinstance(term, str) or (
            isinstance(term, tuple) and term[0] == "L" and not self.stack)

    def step(self):
        if self.halted:
            return False
        term, env = self.current.term, self.current.environment
        if isinstance(term, int):
            if not 0 <= term < len(env):
                raise ValueError("unbound variable in reference lambda term")
            self.current = env[term]
        elif term[0] == "A":
            self.stack.append(Closure(term[2], env))
            self.current = Closure(term[1], env)
        else:
            self.current = Closure(term[1], (self.stack.pop(),) + env)
        self.steps += 1
        return True

    def run(self, budget):
        if budget < 0:
            raise ValueError("budget must be nonnegative")
        for _ in range(budget):
            if not self.step():
                break
        return "value" if self.halted else "suspended"


IDENTITY = named(r"\x. x")
TRUE = named(r"\x y. x")
FALSE = named(r"\x y. y")
CONS = named(r"\x y f. f x y")
NIL = FALSE
OMEGA = app(named(r"\x. x x"), named(r"\x. x x"))


def bitlist(bits):
    """Representation only: builds booleans and pairs, without parsing code."""
    if any(bit not in "01" for bit in bits):
        raise ValueError("expected bits")
    result = NIL
    for bit in reversed(bits):
        result = app(CONS, TRUE if bit == "0" else FALSE, result)
    return result


def normalize(term, budget=100000):
    """Full normal form for semantic tests; raises TimeoutError on fuel exhaustion.

    Fresh neutral probes stand for binders during quotation. They are inspection
    machinery, not constants available to programs or their self-interpreter.
    """
    remaining = budget

    def quote(closure, depth):
        nonlocal remaining
        machine = Machine(closure)
        status = machine.run(remaining)
        remaining -= machine.steps
        if status == "suspended" or remaining == 0:
            raise TimeoutError("normalization budget exhausted")
        current = machine.current
        if isinstance(current.term, str):
            node = depth - 1 - int(current.term)
            for argument in reversed(machine.stack):
                node = app(node, quote(argument, depth))
            return node
        # Enter the lambda's body with a fresh neutral bound variable.
        body = Closure(current.term[1], (Closure(str(depth)),) + current.environment)
        remaining -= 1
        return lam(quote(body, depth + 1))

    return quote(term if isinstance(term, Closure) else Closure(term), 0)


def read_bits(term, budget=100000, limit=100):
    """Observe a Church-encoded bit list; unusual values remain valid programs."""
    remaining, output = budget, []
    cons_tag = named(r"\head tail ignored yes no. yes")

    def evaluate(value, arguments):
        nonlocal remaining
        machine = Machine(value, arguments)
        status = machine.run(remaining)
        remaining -= machine.steps
        if status == "suspended":
            raise TimeoutError
        return machine.current, machine.stack

    value = term
    status = "limit"
    try:
        for _ in range(limit):
            tag, pending = evaluate(value, (cons_tag, FALSE, "cons", "nil"))
            if tag.term == "nil" and not pending:
                status = "end"
                break
            if tag.term != "cons" or pending:
                status = "non-list-value"
                break
            head, _ = evaluate(value, (TRUE,))
            bit, pending = evaluate(head, ("0", "1"))
            if bit.term not in ("0", "1") or pending:
                status = "non-bit-value"
                break
            output.append(bit.term)
            value, _ = evaluate(value, (FALSE,))
    except TimeoutError:
        status = "suspended"
    return dict(output="".join(output), status=status, host_steps=budget - remaining)


def shift(term, amount, cutoff=0):
    if isinstance(term, int):
        return term + amount if term >= cutoff else term
    if term[0] == "L":
        return lam(shift(term[1], amount, cutoff + 1))
    return app(shift(term[1], amount, cutoff), shift(term[2], amount, cutoff))


def beta(body, argument, depth=0):
    """Capture-avoiding contraction of (lambda body) argument."""
    if isinstance(body, int):
        if body == depth:
            return shift(argument, depth)
        return body - 1 if body > depth else body
    if body[0] == "L":
        return lam(beta(body[1], argument, depth + 1))
    return app(beta(body[1], argument, depth), beta(body[2], argument, depth))


def contractions(term):
    """All one-beta-step reducts, with paths for independently replayable proofs."""
    if isinstance(term, int):
        return
    if term[0] == "A" and isinstance(term[1], tuple) and term[1][0] == "L":
        yield (), beta(term[1][1], term[2])
    for path, child in contractions(term[1]):
        yield (1,) + path, (term[0], child, *term[2:])
    if term[0] == "A":
        for path, child in contractions(term[2]):
            yield (2,) + path, app(term[1], child)


def contract_at(term, path):
    if not path:
        if not (isinstance(term, tuple) and term[0] == "A" and
                isinstance(term[1], tuple) and term[1][0] == "L"):
            raise ValueError("path does not identify a beta redex")
        return beta(term[1][1], term[2])
    children = list(term)
    children[path[0]] = contract_at(children[path[0]], path[1:])
    return tuple(children)
