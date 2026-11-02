"""Deterministic bounded beta-contraction search."""

from core.lambda_calculus import contractions, encode


def search(seed, rounds=20, beam=256, slack=400):
    """Bounded, deterministic beta-reduction search; never a minimality proof."""
    seed_bits = encode(seed)
    best, proof = seed, []
    frontier = [(seed, [])]
    seen = {seed}
    generated = 0
    for _ in range(rounds):
        candidates = []
        ceiling = len(encode(best)) + slack
        for term, history in frontier:
            for path, reduct in contractions(term):
                if reduct in seen:
                    continue
                seen.add(reduct)
                generated += 1
                bits = encode(reduct)
                if len(bits) > ceiling:
                    continue
                trail = history + [path]
                candidates.append((len(bits), bits, reduct, trail))
                if len(bits) < len(encode(best)):
                    best, proof = reduct, trail
        if not candidates:
            break
        candidates.sort(key=lambda item: (item[0], item[1]))
        frontier = [(term, history) for _, _, term, history in candidates[:beam]]
    return best, dict(seed_bits=len(seed_bits), result_bits=len(encode(best)),
                      generated=generated, rounds=rounds, beam=beam, slack=slack,
                      beta_paths=proof)
