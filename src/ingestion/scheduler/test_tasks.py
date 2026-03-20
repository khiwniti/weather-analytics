"""
Tests for Celery task scheduler.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.ingestion.scheduler.tasks import (
    app,
    ingest_gfs_cycle,
    ingest_hrrr_cycle,
    ingest_all_sources,
)


@pytest.fixture
def celery_app():
    """Provide Celery app for testing."""
    app.conf.update(task_always_eager=True, task_eager_propagates=True)
    return app


class TestIngestGfsCycle:
    """Tests for ingest_gfs_cycle task."""

    @patch('src.ingestion.scheduler.tasks.upload_to_s3')
    @patch('src.ingestion.scheduler.tasks.convert_grib_to_zarr')
    @patch('src.ingestion.scheduler.tasks.download_gfs')
    def test_successful_ingestion(self, mock_download, mock_convert, mock_upload, temp_dir):
        """Should successfully download, convert, and return result."""
        # Mock successful download
        mock_files = [
            str(temp_dir / f'gfs.t12z.pgrb2.0p25.f{i:03d}')
            for i in range(3)
        ]
        mock_download.return_value = mock_files

        # Execute task
        result = ingest_gfs_cycle.apply(kwargs={'cycle': '12'}).get()

        # Verify result
        assert result['cycle'] == '12'
        assert result['files_processed'] == 3

        # Verify download was called
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args.kwargs
        assert call_kwargs['cycle'] == '12'
        assert len(call_kwargs['forecast_hours']) == 385  # All forecast hours

        # Verify conversion was called for each file
        assert mock_convert.call_count == 3

    @patch('src.ingestion.scheduler.tasks.download_gfs')
    def test_uses_current_cycle_when_none_provided(self, mock_download):
        """Should determine current cycle if not provided."""
        mock_download.return_value = []

        # Mock current time at 10 AM UTC (should use 06Z cycle)
        with patch('src.ingestion.scheduler.tasks.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 1, 10, 0, 0)

            result = ingest_gfs_cycle.apply().get()

        # Should have determined cycle
        assert result['cycle'] in ['00', '06', '12', '18']

    @patch('src.ingestion.scheduler.tasks.download_gfs')
    def test_retries_on_failure(self, mock_download):
        """Should retry task on failure."""
        mock_download.side_effect = Exception('Download failed')

        # Task should raise exception after retries
        with pytest.raises(Exception, match='Download failed'):
            ingest_gfs_cycle.apply(kwargs={'cycle': '12'}).get()

    @patch('src.ingestion.scheduler.tasks.convert_grib_to_zarr')
    @patch('src.ingestion.scheduler.tasks.download_gfs')
    def test_converts_all_downloaded_files(self, mock_download, mock_convert, temp_dir):
        """Should convert all downloaded GRIB files to Zarr."""
        # Mock 10 downloaded files
        mock_files = [
            str(temp_dir / f'gfs.t12z.pgrb2.0p25.f{i:03d}')
            for i in range(10)
        ]
        mock_download.return_value = mock_files

        ingest_gfs_cycle.apply(kwargs={'cycle': '12'}).get()

        # Should convert all 10 files
        assert mock_convert.call_count == 10

        # Verify each file was converted
        for i, call in enumerate(mock_convert.call_args_list):
            args = call[0]
            assert f'f{i:03d}' in args[0]  # GRIB file path
            assert args[1].endswith('.zarr')  # Zarr output path

    @patch('src.ingestion.scheduler.tasks.upload_to_s3')
    @patch('src.ingestion.scheduler.tasks.convert_grib_to_zarr')
    @patch('src.ingestion.scheduler.tasks.download_gfs')
    def test_uploads_to_s3_when_configured(self, mock_download, mock_convert, mock_upload, temp_dir, monkeypatch):
        """Should upload to S3 if S3_WEATHER_BUCKET is set."""
        monkeypatch.setenv('S3_WEATHER_BUCKET', 'test-bucket')

        mock_files = [str(temp_dir / 'gfs.t12z.pgrb2.0p25.f000')]
        mock_download.return_value = mock_files

        ingest_gfs_cycle.apply(kwargs={'cycle': '12'}).get()

        # Should have called upload
        mock_upload.assert_called_once()
        call_args = mock_upload.call_args[0]
        assert call_args[1] == 'test-bucket'  # Bucket name

    @patch('src.ingestion.scheduler.tasks.upload_to_s3')
    @patch('src.ingestion.scheduler.tasks.convert_grib_to_zarr')
    @patch('src.ingestion.scheduler.tasks.download_gfs')
    def test_skips_s3_upload_when_not_configured(self, mock_download, mock_convert, mock_upload, temp_dir, monkeypatch):
        """Should skip S3 upload if S3_WEATHER_BUCKET not set."""
        monkeypatch.delenv('S3_WEATHER_BUCKET', raising=False)

        mock_files = [str(temp_dir / 'gfs.t12z.pgrb2.0p25.f000')]
        mock_download.return_value = mock_files

        ingest_gfs_cycle.apply(kwargs={'cycle': '12'}).get()

        # Should NOT have called upload
        mock_upload.assert_not_called()


class TestIngestHrrrCycle:
    """Tests for ingest_hrrr_cycle task."""

    @patch('src.ingestion.scheduler.tasks.convert_grib_to_zarr')
    @patch('src.ingestion.scheduler.tasks.download_hrrr')
    def test_successful_ingestion(self, mock_download, mock_convert, temp_dir):
        """Should successfully download and convert HRRR data."""
        mock_files = [
            str(temp_dir / f'hrrr.t12z.wrfsfcf{i:02d}.grib2')
            for i in range(5)
        ]
        mock_download.return_value = mock_files

        result = ingest_hrrr_cycle.apply(kwargs={'cycle': '12'}).get()

        assert result['cycle'] == '12'
        assert result['files_processed'] == 5

        # Verify download with correct parameters
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args.kwargs
        assert call_kwargs['cycle'] == '12'
        assert len(call_kwargs['forecast_hours']) == 19  # 0-18 hours

        # Verify all files converted
        assert mock_convert.call_count == 5

    @patch('src.ingestion.scheduler.tasks.download_hrrr')
    def test_uses_current_hour_when_none_provided(self, mock_download):
        """Should use current UTC hour if cycle not provided."""
        mock_download.return_value = []

        with patch('src.ingestion.scheduler.tasks.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 1, 15, 30, 0)

            result = ingest_hrrr_cycle.apply().get()

        # Should use hour 15
        assert result['cycle'] == '15'

    @patch('src.ingestion.scheduler.tasks.download_hrrr')
    def test_handles_download_failure(self, mock_download):
        """Should handle and retry on download failure."""
        mock_download.side_effect = Exception('HRRR download failed')

        with pytest.raises(Exception, match='HRRR download failed'):
            ingest_hrrr_cycle.apply(kwargs={'cycle': '12'}).get()


class TestIngestAllSources:
    """Tests for ingest_all_sources task."""

    @patch('src.ingestion.scheduler.tasks.ingest_hrrr_cycle')
    @patch('src.ingestion.scheduler.tasks.ingest_gfs_cycle')
    def test_chains_gfs_and_hrrr_tasks(self, mock_gfs, mock_hrrr):
        """Should chain GFS and HRRR ingestion tasks."""
        # Mock task signatures
        mock_gfs.s = MagicMock(return_value=Mock())
        mock_hrrr.s = MagicMock(return_value=Mock())

        with patch('src.ingestion.scheduler.tasks.chain') as mock_chain:
            mock_workflow = Mock()
            mock_chain.return_value = mock_workflow

            result = ingest_all_sources.apply().get()

            # Verify chain was created
            mock_chain.assert_called_once()

            # Verify workflow was applied
            mock_workflow.apply_async.assert_called_once()


class TestTaskConfiguration:
    """Tests for Celery task configuration."""

    def test_task_retry_configuration(self):
        """Should have correct retry settings."""
        task = ingest_gfs_cycle

        assert task.max_retries == 3
        assert hasattr(task, 'retry')

    def test_app_configuration(self):
        """Should have correct Celery app configuration."""
        conf = app.conf

        assert conf.task_serializer == 'json'
        assert conf.accept_content == ['json']
        assert conf.result_serializer == 'json'
        assert conf.timezone == 'UTC'
        assert conf.enable_utc is True
        assert conf.task_acks_late is True
        assert conf.task_reject_on_worker_lost is True
        assert conf.task_default_retry_delay == 300
        assert conf.task_max_retries == 3

    def test_broker_url_configuration(self):
        """Should use Redis as broker."""
        broker_url = app.conf.broker_url
        assert 'redis://' in broker_url

    def test_result_backend_configuration(self):
        """Should use Redis as result backend."""
        result_backend = app.conf.result_backend
        assert 'redis://' in result_backend
