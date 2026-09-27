"""v0.4 tests: model manager, inference routing, honest provenance and
graceful fallback when no local model is present.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from brain.inference import (
    InferenceRouter, OfflineFallbackProvider, CloudFallbackProvider,
    CloudConfig, build_inference_router,
)
from brain.llm_interface import MockLLM, ModelConfig
from brain.model_manager import ModelManager, MODEL_REGISTRY


def run(coro):
    return asyncio.run(coro)


# --- model registry / manager --------------------------------------------

def test_registry_has_balanced_models_in_target_range():
    specs = ModelManager.list_specs()
    assert len(specs) >= 3
    # At least one model sits in the spec's ~2-5 GB band.
    assert any(1800 <= s.approx_size_mb <= 5200 for s in specs)


def test_status_without_model_is_not_usable():
    manager = ModelManager(models_dir=tempfile.mkdtemp())
    status = manager.status()
    assert status.present is False
    assert status.usable is False
    assert "model" in status.reason.lower()


def test_import_model_copies_and_reports(tmp_path):
    src = tmp_path / "custom.gguf"
    src.write_bytes(b"GGUF-fake-bytes")
    manager = ModelManager(models_dir=str(tmp_path / "models"))
    status = manager.import_model(str(src))
    assert status.present and status.usable
    assert (tmp_path / "models" / "custom.gguf").exists()


def test_import_missing_source_is_honest(tmp_path):
    manager = ModelManager(models_dir=str(tmp_path / "models"))
    status = manager.import_model(str(tmp_path / "nope.gguf"))
    assert status.present is False
    assert "does not exist" in status.reason.lower()


def test_storage_info_lists_installed(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "x.gguf").write_bytes(b"0" * 1024)
    info = ModelManager(models_dir=str(tmp_path / "models")).storage_info()
    assert info["installed_count"] == 1
    assert info["installed"][0]["name"] == "x.gguf"


def test_download_without_url_is_honest(tmp_path):
    spec = next(s for s in MODEL_REGISTRY if not s.url)
    manager = ModelManager(models_dir=str(tmp_path / "models"))
    status = manager.download_model(spec.id)
    assert status.present is False
    assert "import" in status.reason.lower()


# --- router / fallback ----------------------------------------------------

def test_router_without_local_model_uses_labelled_fallback():
    router = build_inference_router(model_path=str(Path(tempfile.gettempdir()) / "missing.gguf"))
    response = run(router.generate("hello"))
    assert response.origin == "fallback"
    assert response.is_local is False
    assert "offline fallback" in response.text.lower()
    assert router.describe_active_origin() == "fallback"


def test_router_with_mock_reports_mock_origin():
    router = build_inference_router(allow_mock=True)
    response = run(router.generate("hello"))
    assert response.origin == "mock"


def test_router_prefers_available_local():
    router = InferenceRouter(local=MockLLM(["local answer"]))
    response = run(router.generate("hi"))
    assert response.text == "local answer"
    assert response.origin == "mock"  # MockLLM labels itself truthfully


def test_local_failure_falls_through_to_fallback():
    class BrokenLLM(MockLLM):
        def is_available(self):
            return True

        async def generate(self, prompt, config=None):
            raise RuntimeError("boom")

    router = InferenceRouter(local=BrokenLLM())
    response = run(router.generate("hi"))
    assert response.origin == "fallback"
    assert "boom" in router.last_error


def test_cloud_disabled_is_unavailable():
    provider = CloudFallbackProvider(CloudConfig(enabled=False))
    assert provider.is_available() is False
    with pytest.raises(RuntimeError):
        run(provider.generate("hi"))


def test_cloud_enabled_without_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("ASHU_CLOUD_API_KEY", raising=False)
    provider = CloudFallbackProvider(CloudConfig(enabled=True, api_key_env="ASHU_CLOUD_API_KEY"))
    assert provider.is_available() is False


def test_cloud_enabled_with_key_reports_available(monkeypatch):
    monkeypatch.setenv("ASHU_CLOUD_API_KEY", "test-key-not-real")
    provider = CloudFallbackProvider(CloudConfig(enabled=True, api_key_env="ASHU_CLOUD_API_KEY"))
    assert provider.is_available() is True
    info = provider.get_model_info()
    # The key itself is never exposed in the capability report.
    assert "test-key-not-real" not in str(info)
    assert info["has_credentials"] is True


def test_offline_fallback_is_not_claimed_as_a_model():
    provider = OfflineFallbackProvider()
    info = provider.get_model_info()
    assert info["is_model"] is False


def test_agent_reports_fallback_notice_when_no_model(tmp_path):
    # create_agent without a model should produce an honest notice on a real
    # generation turn (not on rule-based onboarding replies).
    from brain.agent import create_agent
    agent = create_agent(db_path=str(tmp_path / "a.db"))
    agent.memory.update_user_profile(name="Arya", nickname="Arya", interests=["coding"], onboarding_completed=True)
    response = run(agent.process_message("Tell me something interesting"))
    assert response.origin in ("fallback", "rule_based", "cloud", "local")
    if response.origin == "fallback":
        assert response.model_notice
        assert response.is_local is False
