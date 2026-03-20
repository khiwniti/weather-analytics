"""
Tests for temporal quality control module.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.processing.qc.temporal_qc import (
    check_temporal_consistency,
    _ensure_dataframe,
)


@pytest.fixture
def valid_weather_data():
    """Create valid weather data with reasonable changes."""
    dates = pd.date_range('2024-01-01', periods=24, freq='H')
    return pd.DataFrame({
        'temperature': [70 + i * 0.5 for i in range(24)],  # Gradual change
        'pressure': [1013 + np.sin(i / 4) * 2 for i in range(24)],  # Sinusoidal
    }, index=dates)


@pytest.fixture
def invalid_weather_data():
    """Create weather data with unrealistic jumps."""
    dates = pd.date_range('2024-01-01', periods=24, freq='H')
    temps = [70] * 24
    temps[10] = 150  # Unrealistic spike
    temps[15] = -20  # Unrealistic drop

    return pd.DataFrame({
        'temperature': temps,
    }, index=dates)


class TestCheckTemporalConsistency:
    """Tests for check_temporal_consistency function."""

    def test_passes_with_valid_data(self, valid_weather_data):
        """Should pass when data changes are reasonable."""
        is_consistent, flagged = check_temporal_consistency(
            valid_weather_data,
            'temperature',
            max_change=10.0  # Allow up to 10°F per hour
        )

        assert is_consistent is True
        assert len(flagged) == 0

    def test_flags_unrealistic_changes(self, invalid_weather_data):
        """Should flag hours with unrealistic changes."""
        is_consistent, flagged = check_temporal_consistency(
            invalid_weather_data,
            'temperature',
            max_change=10.0
        )

        assert is_consistent is False
        assert len(flagged) > 0

    def test_handles_missing_variable(self, valid_weather_data):
        """Should handle gracefully when variable doesn't exist."""
        is_consistent, flagged = check_temporal_consistency(
            valid_weather_data,
            'nonexistent_variable',
            max_change=10.0
        )

        assert is_consistent is True
        assert len(flagged) == 0

    def test_handles_empty_dataframe(self):
        """Should handle empty DataFrame."""
        df = pd.DataFrame()

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=10.0
        )

        assert is_consistent is True
        assert len(flagged) == 0

    def test_detects_multiple_anomalies(self):
        """Should detect multiple anomalous points."""
        dates = pd.date_range('2024-01-01', periods=10, freq='H')
        temps = [70, 71, 90, 72, 73, 110, 74, 75, 76, 77]  # Two spikes

        df = pd.DataFrame({'temperature': temps}, index=dates)

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=5.0
        )

        assert is_consistent is False
        assert len(flagged) >= 2  # Should flag at least 2 anomalies

    def test_respects_max_change_threshold(self, valid_weather_data):
        """Should respect the max_change parameter."""
        # With high threshold, everything passes
        is_consistent_high, _ = check_temporal_consistency(
            valid_weather_data,
            'temperature',
            max_change=100.0
        )
        assert is_consistent_high is True

        # With very low threshold, flags are raised
        is_consistent_low, flagged_low = check_temporal_consistency(
            valid_weather_data,
            'temperature',
            max_change=0.1
        )
        assert is_consistent_low is False
        assert len(flagged_low) > 0

    def test_handles_single_value(self):
        """Should handle DataFrame with single value."""
        df = pd.DataFrame(
            {'temperature': [70]},
            index=[datetime(2024, 1, 1)]
        )

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=10.0
        )

        assert is_consistent is True
        assert len(flagged) == 0

    def test_returns_correct_indices(self, invalid_weather_data):
        """Should return correct indices of flagged values."""
        is_consistent, flagged = check_temporal_consistency(
            invalid_weather_data,
            'temperature',
            max_change=10.0
        )

        # Flagged indices should be actual datetime indices
        for idx in flagged:
            assert isinstance(idx, (pd.Timestamp, datetime))

    def test_handles_unsorted_data(self):
        """Should handle unsorted time series data."""
        dates = pd.date_range('2024-01-01', periods=5, freq='H')
        df = pd.DataFrame(
            {'temperature': [70, 71, 72, 73, 74]},
            index=dates
        )
        # Shuffle the DataFrame
        df = df.sample(frac=1)

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=5.0
        )

        # Should still work (function sorts internally)
        assert isinstance(is_consistent, bool)
        assert isinstance(flagged, list)


class TestEnsureDataframe:
    """Tests for _ensure_dataframe helper function."""

    def test_returns_pandas_dataframe(self):
        """Should return pandas DataFrame as-is."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = _ensure_dataframe(df)

        assert isinstance(result, pd.DataFrame)
        assert result.equals(df)

    @pytest.mark.gpu
    def test_handles_cudf_dataframe(self):
        """Should handle cuDF DataFrame when available."""
        try:
            import cudf

            # Create cuDF DataFrame
            df = cudf.DataFrame({'a': [1, 2, 3]})
            result = _ensure_dataframe(df)

            assert isinstance(result, cudf.DataFrame)
            assert result.equals(df)
        except ImportError:
            pytest.skip("cuDF not available (GPU not present)")

    def test_handles_non_dataframe(self):
        """Should handle non-DataFrame inputs gracefully."""
        # Should just return whatever was passed
        data = {'a': [1, 2, 3]}
        result = _ensure_dataframe(data)

        assert result == data


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_handles_nan_values(self):
        """Should handle NaN values in data."""
        dates = pd.date_range('2024-01-01', periods=5, freq='H')
        df = pd.DataFrame(
            {'temperature': [70, 71, np.nan, 73, 74]},
            index=dates
        )

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=5.0
        )

        # Should handle NaN without crashing
        assert isinstance(is_consistent, bool)

    def test_handles_infinite_values(self):
        """Should handle infinite values in data."""
        dates = pd.date_range('2024-01-01', periods=5, freq='H')
        df = pd.DataFrame(
            {'temperature': [70, 71, np.inf, 73, 74]},
            index=dates
        )

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=5.0
        )

        assert is_consistent is False  # Inf should be flagged

    def test_handles_zero_max_change(self):
        """Should handle zero max_change threshold."""
        dates = pd.date_range('2024-01-01', periods=3, freq='H')
        df = pd.DataFrame(
            {'temperature': [70, 70, 70]},  # No change
            index=dates
        )

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=0.0
        )

        assert is_consistent is True  # No changes, should pass

    def test_handles_negative_values(self):
        """Should handle negative temperature values correctly."""
        dates = pd.date_range('2024-01-01', periods=5, freq='H')
        df = pd.DataFrame(
            {'temperature': [-10, -11, -12, -13, -14]},
            index=dates
        )

        is_consistent, flagged = check_temporal_consistency(
            df,
            'temperature',
            max_change=2.0
        )

        assert is_consistent is True  # Changes are within threshold

    def test_exception_handling(self):
        """Should handle exceptions gracefully."""
        # Pass invalid data type
        is_consistent, flagged = check_temporal_consistency(
            "not a dataframe",
            'temperature',
            max_change=10.0
        )

        # Should return safe defaults
        assert is_consistent is False
        assert flagged == []
