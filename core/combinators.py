"""SK combinators and bracket abstraction shared by the languages."""

from functools import lru_cache
from core.lambda_calculus import IDENTITY, TRUE, app, named


S = named(r"\x y z. x z (y z)")
K = TRUE
B = named(r"\f x y. f (x y)")
CONSTANTS = {"S": S, "K": K, "I": IDENTITY}
SK_I = app("S", "K", "K")
SK_B = app("S", app("K", "S"), "K")
SK_C = app("S", app(SK_B, SK_B, "S"), app("K", "K"))



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
