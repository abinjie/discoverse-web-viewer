"""Resolve a qpsolvers backend name for mink IK (mink uses qpsolvers under the hood)."""

import qpsolvers


def resolve_mink_qp_solver(requested: str = "quadprog") -> str:
    """Return ``requested`` if installed, else the first fallback from a short preference list."""
    avail = set(qpsolvers.available_solvers)
    if requested in avail:
        return requested
    for name in ("quadprog", "daqp", "osqp", "proxqp", "cvxopt", "scs", "ecos"):
        if name in avail:
            return name
    raise RuntimeError(
        "No QP solver available for mink IK. Install one, e.g.: pip install 'qpsolvers[quadprog]'"
    )
