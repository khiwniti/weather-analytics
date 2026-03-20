"""
Tests for GFS downloader module.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import responses

from src.ingestion.nwp.gfs_downloader import (
    get_next_cycle_time,
    is_data_available,
    download_gfs,
    GFS_AVAILABILITY_DELAY,
)


class TestGetNextCycleTime:
    """Tests for get_next_cycle_time() function."""

    def test_returns_next_cycle_after_current_hour(self):
        """Should return next 6-hourly cycle after current time."""
        # Test at 5 AM - should return 6Z + delay
        ref_time = datetime(2024, 1, 1, 5, 0, 0)
        result = get_next_cycle_time(ref_time)

        expected = datetime(2024, 1, 1, 6, 0, 0) + GFS_AVAILABILITY_DELAY['06']
        assert result == expected

    def test_returns_00z_next_day_after_18z(self):
        """Should return 00Z next day if past 18Z."""
        ref_time = datetime(2024, 1, 1, 20, 0, 0)
        result = get_next_cycle_time(ref_time)

        expected = datetime(2024, 1, 2, 0, 0, 0) + GFS_AVAILABILITY_DELAY['00']
        assert result == expected

    def test_handles_cycle_boundaries(self):
        """Should correctly handle times at cycle boundaries."""
        # At exactly 00Z
        ref_time = datetime(2024, 1, 1, 0, 0, 0)
        result = get_next_cycle_time(ref_time)

        expected = datetime(2024, 1, 1, 6, 0, 0) + GFS_AVAILABILITY_DELAY['06']
        assert result == expected

    def test_uses_current_time_when_none_provided(self):
        """Should use current UTC time when no reference time given."""
        result = get_next_cycle_time()
        assert isinstance(result, datetime)
        # Should be in the future
        assert result > datetime.utcnow()


class TestIsDataAvailable:
    """Tests for is_data_available() function."""

    @responses.activate
    def test_returns_true_when_data_available(self):
        """Should return True when NOMADS responds with 200."""
        responses.add(
            responses.HEAD,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            status=200,
        )

        result = is_data_available('12', datetime(2024, 1, 1))
        assert result is True

    @responses.activate
    def test_returns_false_when_data_not_available(self):
        """Should return False when NOMADS responds with 404."""
        responses.add(
            responses.HEAD,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            status=404,
        )

        result = is_data_available('12', datetime(2024, 1, 1))
        assert result is False

    @responses.activate
    def test_returns_false_on_network_error(self):
        """Should return False on network errors."""
        responses.add(
            responses.HEAD,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            body=Exception('Network error'),
        )

        result = is_data_available('12', datetime(2024, 1, 1))
        assert result is False

    def test_validates_cycle_format(self):
        """Should handle cycle parameter correctly."""
        with patch('requests.head') as mock_head:
            mock_head.return_value.status_code = 200

            is_data_available('00')
            is_data_available('06')
            is_data_available('12')
            is_data_available('18')

            assert mock_head.call_count == 4


class TestDownloadGfs:
    """Tests for download_gfs() function."""

    @responses.activate
    def test_downloads_requested_forecast_hours(self, temp_dir):
        """Should download all requested forecast hours."""
        # Mock successful downloads
        for hour in range(3):
            responses.add(
                responses.GET,
                'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
                body=b'GRIB2_DATA',
                status=200,
            )

        result = download_gfs(
            cycle='12',
            forecast_hours=[0, 1, 2],
            output_dir=str(temp_dir),
        )

        assert len(result) == 3
        assert all(str(temp_dir) in path for path in result)

    @responses.activate
    def test_continues_on_individual_failure(self, temp_dir):
        """Should continue downloading even if one file fails."""
        # First succeeds, second fails, third succeeds
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            body=b'GRIB2_DATA',
            status=200,
        )
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            status=500,
        )
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            body=b'GRIB2_DATA',
            status=200,
        )

        result = download_gfs(
            cycle='12',
            forecast_hours=[0, 1, 2],
            output_dir=str(temp_dir),
        )

        # Should have downloaded 2 out of 3
        assert len(result) == 2

    def test_creates_output_directory(self, temp_dir):
        """Should create output directory if it doesn't exist."""
        output_dir = temp_dir / 'nonexistent' / 'nested'

        with patch('urllib.request.urlretrieve'):
            download_gfs(
                cycle='12',
                forecast_hours=[0],
                output_dir=str(output_dir),
            )

        assert output_dir.exists()

    @responses.activate
    def test_constructs_correct_url_parameters(self, temp_dir):
        """Should construct URL with correct parameters."""
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            body=b'GRIB2_DATA',
            status=200,
        )

        download_gfs(
            cycle='12',
            forecast_hours=[0],
            output_dir=str(temp_dir),
            variables=['TMP', 'UGRD'],
            pressure_levels=[1000, 500],
            bbox=(-180, 180, 90, -90),
        )

        # Check that request was made with correct params
        assert len(responses.calls) == 1
        request_url = responses.calls[0].request.url

        # Verify key parameters
        assert 'var_TMP=on' in request_url
        assert 'var_UGRD=on' in request_url
        assert 'lev_1000_mb=on' in request_url
        assert 'lev_500_mb=on' in request_url

    @responses.activate
    def test_uses_default_parameters(self, temp_dir):
        """Should use sensible defaults when parameters not provided."""
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            body=b'GRIB2_DATA',
            status=200,
        )

        result = download_gfs(
            cycle='12',
            forecast_hours=[0],
            output_dir=str(temp_dir),
        )

        assert len(result) == 1
        request_url = responses.calls[0].request.url

        # Check default variables are included
        assert 'var_TMP=on' in request_url
        assert 'var_UGRD=on' in request_url

    @pytest.mark.slow
    @responses.activate
    def test_handles_large_number_of_files(self, temp_dir):
        """Should handle downloading many files without issues."""
        # Simulate downloading 100 files
        for _ in range(100):
            responses.add(
                responses.GET,
                'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
                body=b'GRIB2_DATA',
                status=200,
            )

        result = download_gfs(
            cycle='12',
            forecast_hours=list(range(100)),
            output_dir=str(temp_dir),
        )

        assert len(result) == 100

    def test_returns_empty_list_on_complete_failure(self, temp_dir):
        """Should return empty list if all downloads fail."""
        with patch('urllib.request.urlretrieve', side_effect=Exception('Network error')):
            result = download_gfs(
                cycle='12',
                forecast_hours=[0, 1, 2],
                output_dir=str(temp_dir),
            )

        assert result == []
