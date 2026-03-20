"""Temporal consistency quality control utilities.

Implements checks for unrealistic changes between consecutive time steps.
Supports both cuDF (GPU) and pandas (CPU fallback).
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def _ensure_dataframe(df):
    """Ensure df is a cuDF DataFrame if available, else pandas DataFrame."""
    try:
        import cudf

        if isinstance(df, cudf.DataFrame):
            return df
    except Exception:
        pass
    # Assume pandas
    return df


def check_temporal_consistency(
    df, variable: str, max_change: float
) -> Tuple[bool, list]:
    """Check temporal consistency for a variable.

    Args:
        df: DataFrame with a datetime index and variable column.
        variable: Column name to check.
        max_change: Maximum allowed absolute change per hour.

    Returns:
        Tuple[bool, list]: (is_consistent, list_of_flagged_indices)
    """
    df = _ensure_dataframe(df)
    if variable not in df.columns:
        logger.warning(f"Variable {variable} not in DataFrame")
        return True, []

    # Ensure datetime sorted
    if hasattr(df, "sort_index"):
        df = df.sort_index()

    # Compute diff per hour
    try:
        diff = df[variable].diff().abs()
        # Assuming index is hourly frequency
        flagged = diff > max_change
        indices = df[flagged].index.tolist()
        return len(indices) == 0, indices
    except Exception as e:
        logger.error(f"Temporal QC failed: {e}")
        return False, []
