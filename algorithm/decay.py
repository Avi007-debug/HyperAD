"""
HyperAD — Temporal Decay Engine.

Computes edge weights using exponential decay:
    w(e, t) = base_risk(edge_type) * exp(-lambda * days_since_last_use)

As t → ∞ (stale / unused account), weight → 0.
As t → 0 (used today), weight → base_risk (full danger).

EXTRA: also exposes a sensitivity analysis so you can see how lambda
       affects scoring — useful for the paper's parameter-tuning section.
"""

from __future__ import annotations
import math
import logging
from typing import Dict, Optional, Tuple

from algorithm.models import BASE_RISK, EdgeType

logger = logging.getLogger(__name__)

# Default decay constant.  At λ=0.02, an edge unused for 180 days retains
# only ~2.7% of its base risk.  Tune this for your lab results.
DEFAULT_LAMBDA = 0.02

# Cap staleness at 365 days — beyond that it's effectively zero anyway.
MAX_STALENESS_DAYS = 365

# Minimum absolute floor. Keep at 0.0 so high-risk edges still remain
# strictly higher than low-risk edges even at max staleness.
MIN_WEIGHT_FLOOR = 0.0


def temporal_weight(
    edge_type: str,
    days_since_last_use: Optional[int],
    *,
    lam: float = DEFAULT_LAMBDA,
    floor: float = MIN_WEIGHT_FLOOR,
) -> float:
    """
    Compute temporal decay weight for one edge.

    Args:
        edge_type:            The EdgeType string (e.g. "GenericAll").
        days_since_last_use:  Days since the account/permission was last observed
                              active.  None means 'never seen used' — treated as
                              MAX_STALENESS_DAYS.
        lam:                  Decay constant λ.  Higher = steeper decay.
        floor:                Minimum weight — prevents division-by-zero in
                              shortest-path inversion and reflects residual risk.

    Returns:
        float: weight in range [floor, base_risk].
    """
    base = BASE_RISK.get(edge_type, 1.0)

    if days_since_last_use is None:
        days = MAX_STALENESS_DAYS
    else:
        days = min(max(days_since_last_use, 0), MAX_STALENESS_DAYS)

    decay  = math.exp(-lam * days)
    weight = base * decay

    # Enforce floor — residual risk for completely stale permissions
    weight = max(weight, floor)

    logger.debug(
        "temporal_weight | type=%s base=%.2f days=%d λ=%.3f → %.4f",
        edge_type, base, days, lam, weight,
    )
    return round(weight, 6)


def invert_weight(weight: float) -> float:
    """
    Invert a risk weight for use as a shortest-path cost.

    Bellman-Ford finds the *minimum* cost path.  We want the *maximum* risk
    path.  Solution: treat cost = 1 / weight so that high-risk edges have
    low cost and are preferred.

    Args:
        weight: The raw temporal weight (higher = more dangerous).

    Returns:
        float: Inverted cost for Bellman-Ford.
    """
    return round(1.0 / max(weight, 1e-9), 6)


def score_path_weights(weights: list[float]) -> float:
    """
    Aggregate per-edge weights into a single path risk score.

    Strategy: sum of weights.  A longer path through many high-risk edges
    scores higher than a short path through one medium-risk edge.

    Args:
        weights: List of temporal weights along the path.

    Returns:
        float: Aggregate risk score.
    """
    return round(sum(weights), 4)


# ── EXTRA: Sensitivity analysis ───────────────────────────────────────────────
def lambda_sensitivity(
    edge_type: str,
    lambdas: Tuple[float, ...] = (0.005, 0.01, 0.02, 0.05, 0.1),
    day_checkpoints: Tuple[int, ...] = (0, 7, 30, 90, 180, 365),
) -> Dict[str, Dict[int, float]]:
    """
    Extra feature — not in any existing AD tool.

    Shows how the same edge type scores across different λ values and
    staleness checkpoints.  Used to:
      - Choose the best λ for your lab environment
      - Generate Table 2 in the IEEE paper (parameter sensitivity)
      - Justify the λ=0.02 default

    Returns:
        Nested dict:  {lambda_value: {days: weight}}

    Example output (GenericAll, base_risk=10):
        λ=0.02  →  day=0: 10.0,  day=30: 5.49,  day=180: 0.27
        λ=0.05  →  day=0: 10.0,  day=30: 2.23,  day=180: 0.05
    """
    results: Dict[str, Dict[int, float]] = {}
    for lam in lambdas:
        key = f"λ={lam}"
        results[key] = {
            d: temporal_weight(edge_type, d, lam=lam)
            for d in day_checkpoints
        }
    return results


def print_sensitivity_table(edge_type: str = EdgeType.GENERIC_ALL) -> None:
    """Pretty-print sensitivity table to stdout. Useful during development."""
    table = lambda_sensitivity(edge_type)
    days  = (0, 7, 30, 90, 180, 365)
    header = f"{'Lambda':<12}" + "".join(f"{'day '+str(d):>10}" for d in days)
    print(f"\nSensitivity analysis for edge type: {edge_type}")
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for lam_key, day_map in table.items():
        row = f"{lam_key:<12}" + "".join(f"{day_map[d]:>10.4f}" for d in days)
        print(row)
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    print_sensitivity_table(EdgeType.GENERIC_ALL)
    print_sensitivity_table(EdgeType.DC_SYNC)
    print_sensitivity_table(EdgeType.MEMBER_OF)
