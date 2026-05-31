"""Tests for QThread worker lifecycle and signals."""

import os
import time

import pytest


class TestUploadWorkerSignals:
    def test_cancel_before_start_no_signals(self, qtbot, temp_bruker_zip, mock_server):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import UploadWorker

        api = SpectrumMatcherApi(server_url=mock_server, timeout=5)
        worker = UploadWorker(temp_bruker_zip, api)
        worker.cancel()

        finished_called = []
        error_called = []
        worker.finished.connect(lambda d: finished_called.append(d))
        worker.error.connect(lambda m: error_called.append(m))
        worker.start()
        worker.wait(2000)

        assert len(finished_called) == 0
        assert len(error_called) == 0

    def test_upload_to_mock_emits_finished(self, qtbot, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import UploadWorker

        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        worker = UploadWorker(sample_zip, api)
        with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
            worker.start()
        data = blocker.args[0]
        assert "results" in data
        assert len(data["results"]) == 13

    def test_upload_with_bruker_zip(self, qtbot, mock_server, temp_bruker_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import UploadWorker

        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        worker = UploadWorker(temp_bruker_zip, api)
        with qtbot.waitSignal(worker.finished, timeout=5000):
            worker.start()

    def test_progress_signal_emitted(self, qtbot, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import UploadWorker

        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        worker = UploadWorker(sample_zip, api)
        progress_events = []
        worker.progress.connect(lambda s, t: progress_events.append((s, t)))
        with qtbot.waitSignal(worker.finished, timeout=10000):
            worker.start()
        assert len(progress_events) >= 1
        for sent, total in progress_events:
            assert sent <= total
            assert total > 0

    def test_error_signal_on_bad_url(self, qtbot):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import UploadWorker

        api = SpectrumMatcherApi(server_url="http://127.0.0.1:1", timeout=2)
        worker = UploadWorker(__file__, api)
        with qtbot.waitSignal(worker.error, timeout=5000):
            worker.start()

    def test_cancel_mid_upload(self, qtbot, configurable_mock_server):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import UploadWorker

        api = SpectrumMatcherApi(
            server_url=configurable_mock_server, timeout=10
        )
        worker = UploadWorker(__file__, api)
        finished_called = []
        worker.finished.connect(lambda d: finished_called.append(d))
        worker.start()
        time.sleep(0.1)
        worker.cancel()
        worker.wait(3000)
        assert len(finished_called) == 0


class TestHealthCheckWorker:
    def test_ok(self, mock_server):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import HealthCheckWorker

        api = SpectrumMatcherApi(server_url=mock_server, timeout=5)
        worker = HealthCheckWorker(api)
        # Sync test — just call run directly
        worker.run()
        # Can't easily test QThread signal sync; just verify no exception

    def test_fail(self):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import HealthCheckWorker

        api = SpectrumMatcherApi(server_url="http://127.0.0.1:1", timeout=2)
        worker = HealthCheckWorker(api)
        worker.run()


class TestZipFolder:
    def test_creates_valid_zip(self, temp_dir, sample_dir):
        from spectrum_matcher_client.workers import _zip_folder
        import zipfile
        zip_path = _zip_folder(sample_dir)
        assert os.path.exists(zip_path)
        assert zipfile.is_zipfile(zip_path)
        os.unlink(zip_path)

    def test_missing_pdata_raises(self, temp_dir):
        from spectrum_matcher_client.workers import _zip_folder
        os.makedirs(os.path.join(temp_dir, "no_pdata_here"))
        with pytest.raises(ValueError, match="pdata"):
            _zip_folder(os.path.join(temp_dir, "no_pdata_here"))

    def test_nonexistent_raises(self):
        from spectrum_matcher_client.workers import _zip_folder
        with pytest.raises(ValueError):
            _zip_folder("/nonexistent/path/12345")
