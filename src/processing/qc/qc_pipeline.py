"""QC pipeline orchestration.

Runs a series of QC checks defined in a configuration dictionary.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

from .temporal_qc import check_temporal_consistency
from .gap_filling import fill_gaps


def run_qc_pipeline(df, config: Dict[str, Any]):
    """Run QC pipeline on a DataFrame.

    Config structure example::

        variables:
            temperature:
                max_change: 10
            pressure:
                max_change: 10
            wind_speed:
                max_change: 30
            precipitation:
                min: 0

    Args:
        df: DataFrame (cudf or pandas) with a datetime index.
        config: QC configuration.

    Returns:
        DataFrame with QC flags applied (in-place modifications).
    """
    variables_cfg = config.get("variables", {})
    for var, settings in variables_cfg.items():
        max_change = settings.get("max_change")
        min_val = settings.get("min")
        # Temporal consistency check
        if max_change is not None:
            consistent, flagged = check_temporal_consistency(df, var, max_change)
            if not consistent:
                logger.info(f"Temporal QC flagged {len(flagged)} points for {var}")
        # Minimum value check (e.g., precipitation)
        if min_val is not None:
            # Flag negative values
            if (df[var] < min_val).any():
                logger.info(f"QC: {var} contains values below {min_val}")
        # Gap filling after flags
        success, filled = fill_gaps(df, var)
        if success:
            logger.info(f"Filled {filled} missing values for {var}")
    return df
