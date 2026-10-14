"""Entity-level F0.5, the challenge metric.

For each Source 1 entity we compare the predicted set of S2/S3 ids with the
true set:

    precision = |pred & true| / |pred|
    recall    = |pred & true| / |true|
    F0.5      = 1.25 * P * R / (0.25 * P + R)

Edge cases:
    true empty, pred empty      -> 1.0 (correctly called a singleton)
    true empty, pred non-empty  -> 0.0 (false merge)
    true non-empty, pred empty  -> 0.0 (missed every match)

The final score is the mean over all Source 1 entities. beta = 0.5 weights
precision twice as much as recall, so a wrong merge costs more than a miss.
"""
from __future__ import annotations

from typing import Iterable, Mapping

BETA = 0.5


def entity_f_beta(pred: set, true: set, beta: float = BETA) -> float:
    if not true:
        return 1.0 if not pred else 0.0
    if not pred:
        return 0.0
    tp = len(pred & true)
    if tp == 0:
        return 0.0
    p = tp / len(pred)
    r = tp / len(true)
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r)


def score(pred: Mapping[str, set], true: Mapping[str, set], ids: Iterable[str] | None = None) -> dict:
    """Mean entity F0.5 plus mean precision/recall over `ids` (default: all true ids).

    Precision is averaged over entities where something was predicted, recall
    over entities that have at least one true match.
    """
    ids = list(ids) if ids is not None else list(true)
    f, ps, rs = [], [], []
    for i in ids:
        t = true.get(i, set())
        p = pred.get(i, set())
        f.append(entity_f_beta(p, t))
        if p:
            ps.append(len(p & t) / len(p))
        if t:
            rs.append(len(p & t) / len(t))
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    return {"f05": mean(f), "precision": mean(ps), "recall": mean(rs), "n_entities": len(ids)}


def parse_id_list(cell) -> set:
    if cell is None or (isinstance(cell, float) and cell != cell) or cell == "":
        return set()
    return {x for x in str(cell).split(",") if x}


if __name__ == "__main__":
    assert entity_f_beta(set(), set()) == 1.0
    assert entity_f_beta({"a"}, set()) == 0.0
    assert entity_f_beta(set(), {"a"}) == 0.0
    assert entity_f_beta({"a"}, {"a"}) == 1.0
    # half the predictions right, all true found: P=0.5, R=1
    assert abs(entity_f_beta({"a", "b"}, {"a"}) - 1.25 * 0.5 / (0.125 + 1)) < 1e-12
    # all predictions right, half the true found: P=1, R=0.5 -> scores higher than the case above
    assert entity_f_beta({"a"}, {"a", "b"}) > entity_f_beta({"a", "b"}, {"a"})
    s = score({"x": {"a"}, "y": set()}, {"x": {"a"}, "y": set(), "z": {"c"}})
    assert abs(s["f05"] - 2 / 3) < 1e-12
    print("metric tests pass")
