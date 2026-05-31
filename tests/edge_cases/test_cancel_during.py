"""Edge case tests: cancel operations during upload."""

import time

import pytest


class TestCancelOperations:
    def test_cancel_before_start_prevents_upload(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from spectrum_matcher_client.workers import UploadWorker

        api = SpectrumMatcherApi(server_url=mock_server, timeout=5)
        worker = UploadWorker(sample_zip, api)
        worker.cancel()
        finished_called = []
        worker.finished.connect(lambda d: finished_called.append(d))
        worker.start()
        worker.wait(2000)
        assert len(finished_called) == 0

    def test_cancel_then_new_upload(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi

        api = SpectrumMatcherApi(server_url=mock_server, timeout=15)
        # cancel before first request
        api.cancel()
        assert api._cancel_event.is_set()
        # upload should clear cancel and work
        result = api.upload_zip(sample_zip)
        assert "results" in result
        assert not api._cancel_event.is_set()

    def test_api_cancel_sets_event(self, mock_server):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        api.cancel()
        assert api._cancel_event.is_set()

    def test_api_cancel_cleared_before_upload(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        api.cancel()
        assert api._cancel_event.is_set()
        result = api.upload_zip(sample_zip)
        assert "results" in result
        assert not api._cancel_event.is_set()
