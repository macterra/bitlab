"""Closed lambda wrapper making empty source denote its own decoder."""

from core.lambda_calculus import named


def reflection_seed(base):
    return named(r"(\s. s s) (\s bits. bits (\head tail ignored. base bits) (s s))", {"base": base})
