"""Tests for server/model_runner.py (mock mode)."""

import os
import sys

import pytest

SERVER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "server")
sys.path.insert(0, SERVER_DIR)


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    """Force mock mode by clearing model/data globals before each test."""
    import model_runner
    model_runner._model = None
    model_runner._plant_flavors = None
    model_runner._mock_mode = True
    model_runner._model_config = {}


def _init_mock():
    import model_runner
    model_runner.init()


class TestInit:
    def test_init_runs_without_error(self):
        import model_runner
        model_runner._model = None
        model_runner._plant_flavors = None
        model_runner.init()
        assert model_runner._mock_mode is True

    def test_init_sets_plant_flavors(self):
        import model_runner
        model_runner._model = None
        model_runner._plant_flavors = None
        model_runner.init()
        assert len(model_runner._plant_flavors) == 13

    def test_get_config_returns_dict(self):
        import model_runner
        model_runner.init()
        cfg = model_runner.get_config()
        assert isinstance(cfg, dict)
        assert cfg["name"] == "DeepMID"


class TestMatchMockMode:
    def test_match_returns_expected_keys(self):
        import model_runner
        model_runner.init()
        result = model_runner.match("/fake/path")
        assert "query_name" in result
        assert "query_ppm" in result
        assert "query_fid" in result
        assert "results" in result

    def test_match_returns_13_results(self):
        import model_runner
        model_runner.init()
        result = model_runner.match("/fake/path")
        assert len(result["results"]) == 13

    def test_match_top3_have_ppm_fid(self):
        import model_runner
        model_runner.init()
        result = model_runner.match("/fake/path")
        for i, r in enumerate(result["results"]):
            if i < 3:
                assert "ppm" in r
                assert "fid" in r
            else:
                assert "ppm" not in r
                assert "fid" not in r

    def test_match_probabilities_in_range(self):
        import model_runner
        model_runner.init()
        result = model_runner.match("/fake/path")
        for r in result["results"]:
            assert 0 < r["probability"] <= 1

    def test_match_query_name_is_basename(self):
        import model_runner
        model_runner.init()
        result = model_runner.match("/some/path/my_spectrum")
        assert result["query_name"] == "my_spectrum"


class TestConfigLoading:
    def test_load_config_with_json(self, tmp_path):
        import model_runner
        json_path = tmp_path / "model_config.json"
        json_path.write_text('{"name": "TestModel", "arch": "Test"}')
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(model_runner, "CONFIG_PATH", str(json_path))
        monkeypatch.setattr(model_runner, "SERVER_DIR", str(tmp_path))
        config = model_runner._load_config()
        assert config["name"] == "TestModel"
        assert config["arch"] == "Test"
        monkeypatch.undo()

    def test_load_config_missing_file_uses_defaults(self, tmp_path):
        import model_runner
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(model_runner, "CONFIG_PATH", str(tmp_path / "nonexistent.json"))
        monkeypatch.setattr(model_runner, "SERVER_DIR", str(tmp_path))
        config = model_runner._load_config()
        assert config["name"] == "DeepMID"
        monkeypatch.undo()

    def test_load_config_env_override_model_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPECTRUM_MATCHER_MODEL", "/custom/model.h5")
        import model_runner
        orig_config_path = model_runner.CONFIG_PATH
        monkeypatch.setattr(model_runner, "CONFIG_PATH", str(tmp_path / "nonexistent.json"))
        monkeypatch.setattr(model_runner, "SERVER_DIR", str(tmp_path))
        config = model_runner._load_config()
        assert config["model_path"] == "/custom/model.h5"
        monkeypatch.setattr(model_runner, "CONFIG_PATH", orig_config_path)
