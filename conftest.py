"""
Pytest configuration and shared fixtures.
"""
import os
import pytest
from datetime import datetime
from pathlib import Path

# Set test environment variables
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/15'  # Use different DB for tests
os.environ['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/15'
os.environ['S3_WEATHER_BUCKET'] = ''  # Disable S3 for tests


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_gfs_metadata():
    """Sample GFS metadata for testing."""
    return {
        'cycle': '12',
        'date': datetime.utcnow().strftime('%Y%m%d'),
        'forecast_hours': list(range(0, 384, 6)),  # Every 6 hours
        'variables': ['TMP', 'UGRD', 'VGRD', 'PRATE'],
        'pressure_levels': [1000, 850, 500, 250],
    }


@pytest.fixture
def sample_hrrr_metadata():
    """Sample HRRR metadata for testing."""
    return {
        'cycle': '12',
        'date': datetime.utcnow().strftime('%Y%m%d'),
        'forecast_hours': list(range(0, 19)),  # Hourly
        'variables': ['TMP', 'UGRD', 'VGRD', 'REFC'],
    }


@pytest.fixture
def sample_zarr_path(temp_dir):
    """Path for sample Zarr output."""
    zarr_path = temp_dir / 'test_output.zarr'
    return str(zarr_path)


@pytest.fixture
def mock_grib_file(temp_dir):
    """Create a mock GRIB2 file for testing."""
    grib_path = temp_dir / 'test.grib2'
    # Create empty file (actual GRIB parsing not tested here)
    grib_path.write_bytes(b'GRIB' + b'\x00' * 100)
    return str(grib_path)


@pytest.fixture
def sample_weather_data():
    """Sample weather data for QC testing."""
    import pandas as pd
    import numpy as np

    dates = pd.date_range('2024-01-01', periods=24, freq='H')
    return pd.DataFrame({
        'temperature': 70 + np.random.randn(24) * 5,
        'pressure': 1013 + np.random.randn(24) * 2,
        'humidity': 60 + np.random.randn(24) * 10,
    }, index=dates)


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Clean up temporary test files after each test."""
    yield
    # Cleanup code here if needed
    pass


def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "gpu: mark test as requiring GPU"
    )
