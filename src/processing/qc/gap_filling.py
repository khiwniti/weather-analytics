"""Gap filling utilities for weather data.

Provides simple linear interpolation for flagged values.
Works with cuDF when available, falling back to pandas.
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def _ensure_dataframe(df):
    try:
        import cudf

        if isinstance(df, cudf.DataFrame):
            return df
    except Exception:
        pass
    return df


def fill_gaps(df, variable: str) -> Tuple[bool, int]:
    """Fill gaps (NaNs) in a variable column using linear interpolation.

    Args:
        df: DataFrame with variable column.
        variable: Column name.

    Returns:
        Tuple[bool, int]: (success, number_of_filled_values)
    """
    df = _ensure_dataframe(df)
    if variable not in df.columns:
        logger.warning(f"Variable {variable} not in DataFrame")
        return False, 0
    try:
        before = df[variable].isna().sum()
        df[variable] = df[variable].interpolate(method="linear")
        after = df[variable].isna().sum()
        filled = before - after
        return True, int(filled)
    except Exception as e:
        logger.error(f"Gap filling failed for {variable}: {e}")
        return False, 0
