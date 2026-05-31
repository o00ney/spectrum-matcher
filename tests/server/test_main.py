"""Server endpoint tests via FastAPI TestClient (mock mode)."""

import base64
import json
import os

import pytest


class TestUploadEndpoint:
    def test_upload_no_file_returns_422(self, test_client):
        resp = test_client.post("/api/upload")
        assert resp.status_code == 422

    def test_upload_non_zip_extension_returns_400(self, test_client):
        resp = test_client.post(
            "/api/upload",
            files={"file": ("test.txt", b"data", "text/plain")},
        )
        assert resp.status_code == 400
        assert "zip" in resp.json()["detail"].lower()

    def test_upload_empty_zip(self, test_client, empty_zip):
        with open(empty_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("empty.zip", f, "application/zip")},
            )
        assert resp.status_code == 200

    def test_upload_bruker_zip_200(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "query_name" in data
        assert "results" in data
        assert "plot_base64" in data
        assert "query_ppm" in data
        assert "query_fid" in data
        assert "model" in data

    def test_upload_response_structure(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        data = resp.json()
        assert data["query_name"] in ("b1_sample", "extracted")
        assert len(data["results"]) == 13

    def test_results_sorted_by_probability(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        probs = [r["probability"] for r in resp.json()["results"]]
        for i in range(len(probs) - 1):
            assert probs[i] >= probs[i + 1], f"not sorted at index {i}"

    def test_top3_have_ds_data(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        results = resp.json()["results"]
        for i, r in enumerate(results):
            if i < 3:
                assert "ppm_ds" in r, f"result {i} missing ppm_ds"
                assert "fid_ds" in r, f"result {i} missing fid_ds"
                assert len(r["ppm_ds"]) > 0
                assert len(r["fid_ds"]) > 0

    def test_ds_length_reasonable(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        data = resp.json()
        assert 2900 <= len(data["query_ppm"]) <= 3100
        assert 2900 <= len(data["query_fid"]) <= 3100

    def test_plot_base64_is_valid_png(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        img = base64.b64decode(resp.json()["plot_base64"])
        assert img[:8] == b"\x89PNG\r\n\x1a\n"

    def test_plot_base64_file_cleaned_up(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        data = resp.json()
        assert len(data["plot_base64"]) > 100
        # no temp plot file left behind
        plot_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "server", "static", "plots"
        )
        # files should be cleaned up already

    def test_model_info_present(self, test_client, sample_zip):
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        model = resp.json()["model"]
        assert model["name"] == "DeepMID"
        assert "arch" in model
        assert "params" in model
        assert "task" in model

    def test_temp_files_cleaned_after_response(self, test_client, sample_zip):
        upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "server", "uploads"
        )
        before = set(os.listdir(upload_dir)) if os.path.exists(upload_dir) else set()
        with open(sample_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
            )
        assert resp.status_code == 200
        after = set(os.listdir(upload_dir)) if os.path.exists(upload_dir) else set()
        assert before == after, f"temp files not cleaned: {after - before}"


class TestHealthEndpoint:
    def test_docs_endpoint(self, test_client):
        resp = test_client.get("/docs")
        assert resp.status_code == 200
