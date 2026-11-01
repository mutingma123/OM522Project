"""Method 1, the rule to beat: the earliest due date sequence.

The brief states the rule exactly: sort jobs by due date, break ties by job identifier, and use
that order at every stage. Operation timing follows the shared execution rule in timing.py.
"""

from __future__ import annotations

import numpy as np

from .data import Instance


def edd_sequence(instance: Instance) -> np.ndarray:
    """Return job indices sorted by due date, ties broken by job identifier (string order)."""
    order = sorted(range(instance.n), key=lambda j: (instance.due[j], instance.job_ids[j]))
    return np.array(order, dtype=np.int64)
