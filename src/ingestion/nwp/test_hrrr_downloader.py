"""
Tests for HRRR downloader module.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import responses

from src.ingestion.nwp.hrrr_downloader import (
    get_next_hrrr_cycle,
    is_hrrr_available,
    download_hrrr,
    HRRR_AVAILABILITY_DELAY,
)


class TestGetNextHrrrCycle:
    """Tests for get_next_hrrr_cycle() function."""

    def test_returns_next_hour_cycle(self):
        """Should return next hour cycle with delay."""
        ref_time = datetime(2024, 1, 1, 10, 30, 0)
        result = get_next_hrrr_cycle(ref_time)

        expected = datetime(2024, 1, 1, 11, 0, 0) + HRRR_AVAILABILITY_DELAY
        assert result == expected

    def test_wraps_to_next_day_at_23z(self):
        """Should wrap to 00Z next day after 23Z."""
        ref_time = datetime(2024, 1, 1, 23, 30, 0)
        result = get_next_hrrr_cycle(ref_time)

        expected = datetime(2024, 1, 2, 0, 0, 0) + HRRR_AVAILABILITY_DELAY
        assert result == expected

    def test_handles_early_morning_hours(self):
        """Should correctly handle early morning cycles."""
        ref_time = datetime(2024, 1, 1, 0, 10, 0)
        result = get_next_hrrr_cycle(ref_time)

        expected = datetime(2024, 1, 1, 1, 0, 0) + HRRR_AVAILABILITY_DELAY
        assert result == expected

    def test_uses_current_time_when_none_provided(self):
        """Should use current UTC time when no reference provided."""
        result = get_next_hrrr_cycle()

        assert isinstance(result, datetime)
        assert result > datetime.utcnow()


class TestIsHrrrAvailable:
    """Tests for is_hrrr_available() function."""

    @responses.activate
    def test_returns_true_when_available(self):
        """Should return True when NOMADS data is available."""
        responses.add(
            responses.HEAD,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            status=200,
        )

        result = is_hrrr_available('12', datetime(2024, 1, 1))
        assert result is True

    @responses.activate
    def test_returns_false_when_not_available(self):
        """Should return False when data not available."""
        responses.add(
            responses.HEAD,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            status=404,
        )

        result = is_hrrr_available('12', datetime(2024, 1, 1))
        assert result is False

    @responses.activate
    def test_handles_network_errors(self):
        """Should return False on network errors."""
        responses.add(
            responses.HEAD,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=Exception('Connection error'),
        )

        result = is_hrrr_available('12')
        assert result is False

    def test_validates_all_hourly_cycles(self):
        """Should work for all 24 hourly cycles."""
        with patch('requests.head') as mock_head:
            mock_head.return_value.status_code = 200

            for hour in range(24):
                cycle = f'{hour:02d}'
                result = is_hrrr_available(cycle)
                assert isinstance(result, bool)


class TestDownloadHrrr:
    """Tests for download_hrrr() function."""

    @responses.activate
    def test_downloads_requested_forecast_hours(self, temp_dir):
        """Should download all requested forecast hours."""
        for hour in range(5):
            responses.add(
                responses.GET,
                'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
                body=b'HRRR_GRIB2_DATA',
                status=200,
            )

        result = download_hrrr(
            cycle='12',
            forecast_hours=[0, 1, 2, 3, 4],
            output_dir=str(temp_dir),
        )

        assert len(result) == 5
        assert all(str(temp_dir) in path for path in result)

    @responses.activate
    def test_continues_on_partial_failure(self, temp_dir):
        """Should continue downloading even if some files fail."""
        # Simulate 2 successes, 1 failure, 2 successes
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=b'HRRR_DATA',
            status=200,
        )
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=b'HRRR_DATA',
            status=200,
        )
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            status=500,
        )
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=b'HRRR_DATA',
            status=200,
        )
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=b'HRRR_DATA',
            status=200,
        )

        result = download_hrrr(
            cycle='12',
            forecast_hours=[0, 1, 2, 3, 4],
            output_dir=str(temp_dir),
        )

        # Should have 4 successful downloads
        assert len(result) == 4

    def test_creates_output_directory(self, temp_dir):
        """Should create output directory if missing."""
        output_dir = temp_dir / 'hrrr' / 'nested'

        with patch('urllib.request.urlretrieve'):
            download_hrrr(
                cycle='12',
                forecast_hours=[0],
                output_dir=str(output_dir),
            )

        assert output_dir.exists()

    @responses.activate
    def test_constructs_correct_url(self, temp_dir):
        """Should construct URL with correct parameters."""
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=b'HRRR_DATA',
            status=200,
        )

        download_hrrr(
            cycle='12',
            forecast_hours=[0],
            output_dir=str(temp_dir),
            variables=['TMP', 'UGRD', 'VGRD'],
            bbox=(-125, -65, 50, 25),  # CONUS
        )

        # Verify request
        assert len(responses.calls) == 1
        request_url = responses.calls[0].request.url

        # Check variables
        assert 'var_TMP=on' in request_url
        assert 'var_UGRD=on' in request_url
        assert 'var_VGRD=on' in request_url

    @responses.activate
    def test_uses_default_parameters(self, temp_dir):
        """Should use default variables and bbox when not specified."""
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=b'HRRR_DATA',
            status=200,
        )

        result = download_hrrr(
            cycle='12',
            forecast_hours=[0],
            output_dir=str(temp_dir),
        )

        assert len(result) == 1
        request_url = responses.calls[0].request.url

        # Should include default variables
        assert 'var_' in request_url

    @responses.activate
    def test_handles_all_18_forecast_hours(self, temp_dir):
        """Should handle downloading full 18-hour forecast."""
        for _ in range(19):  # 0-18 inclusive
            responses.add(
                responses.GET,
                'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
                body=b'HRRR_DATA',
                status=200,
            )

        result = download_hrrr(
            cycle='12',
            forecast_hours=list(range(19)),
            output_dir=str(temp_dir),
        )

        assert len(result) == 19

    def test_returns_empty_list_on_total_failure(self, temp_dir):
        """Should return empty list if all downloads fail."""
        with patch('urllib.request.urlretrieve', side_effect=Exception('Network error')):
            result = download_hrrr(
                cycle='12',
                forecast_hours=[0, 1, 2],
                output_dir=str(temp_dir),
            )

        assert result == []

    @responses.activate
    def test_filename_format(self, temp_dir):
        """Should create files with correct naming convention."""
        responses.add(
            responses.GET,
            'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
            body=b'HRRR_DATA',
            status=200,
        )

        result = download_hrrr(
            cycle='12',
            forecast_hours=[3],
            output_dir=str(temp_dir),
        )

        # Check filename format: hrrr.t{cycle}z.wrfsfcf{hour}.grib2
        assert len(result) == 1
        filename = result[0].split('/')[-1]
        assert 'hrrr.t12z.wrfsfcf' in filename
        assert filename.endswith('.grib2')


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_handles_invalid_cycle(self, temp_dir):
        """Should handle invalid cycle gracefully."""
        with patch('urllib.request.urlretrieve', side_effect=Exception('Invalid cycle')):
            result = download_hrrr(
                cycle='99',  # Invalid cycle
                forecast_hours=[0],
                output_dir=str(temp_dir),
            )

        assert result == []

    def test_handles_empty_forecast_hours(self, temp_dir):
        """Should handle empty forecast hours list."""
        result = download_hrrr(
            cycle='12',
            forecast_hours=[],
            output_dir=str(temp_dir),
        )

        assert result == []

    @responses.activate
    def test_handles_special_characters_in_path(self):
        """Should handle paths with special characters."""
        # Create path with spaces and special chars
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'test dir' / 'hrrr data'

            responses.add(
                responses.GET,
                'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl',
                body=b'HRRR_DATA',
                status=200,
            )

            result = download_hrrr(
                cycle='12',
                forecast_hours=[0],
                output_dir=str(output_dir),
            )

            assert len(result) == 1
            assert output_dir.exists()
