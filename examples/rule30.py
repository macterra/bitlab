"""Fixed-width Rule 30 as a closed lambda function, shared by both languages."""

from core.lambda_calculus import CONS, FALSE, NIL, TRUE, named


def local_rule():
    # Encoded zero selects the first argument; encoded one selects the second.
    xor = named(r"\a b. a b (b one zero)", {"zero": TRUE, "one": FALSE})
    return named(r"\left center right. xor left (center right one)",
                 {"xor": xor, "one": FALSE})



def step_function():
    return named(r"""((\s. s s) (\s left xs.
        xs (\center tail ignored.
            cons (rule left center (tail (\head rest ignored. head) zero))
                 (s s center tail)) nil)) zero""",
                 {"cons": CONS, "rule": local_rule(), "zero": TRUE, "nil": NIL})
