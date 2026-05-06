"""Unit tests for GemmaLocalProvider path resolution."""

from pathlib import Path

from core.model.providers.gemma_local import GemmaLocalProvider


def _make_checkpoint_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "config.json").write_text("{}", encoding="utf-8")
    (path / "model.safetensors").write_text("", encoding="utf-8")


def test_resolve_prefers_larger_variant_within_root(tmp_path, monkeypatch) -> None:
    root = tmp_path / "ckpts"
    _make_checkpoint_dir(root / "gemma-4-E2B-it")
    _make_checkpoint_dir(root / "gemma-4-26B-A4B-it")

    monkeypatch.setenv("GEMMA_MODEL_PATH", str(root))
    provider = GemmaLocalProvider(model="/does/not/matter")

    resolved = provider._resolve_model_path()
    assert resolved is not None
    assert resolved.name == "gemma-4-26B-A4B-it"


def test_resolve_uses_candidate_root_when_env_path_invalid(tmp_path, monkeypatch) -> None:
    root = tmp_path / "gemma-root"
    _make_checkpoint_dir(root / "gemma-4-E4B-it")

    monkeypatch.setenv("GEMMA_MODEL_PATH", "/invalid/path")
    provider = GemmaLocalProvider(model="/invalid/too", candidate_roots=[str(root)])

    resolved = provider._resolve_model_path()
    assert resolved is not None
    assert resolved.name == "gemma-4-E4B-it"


def test_health_check_records_attempted_paths_on_failure(monkeypatch) -> None:
    monkeypatch.setenv("GEMMA_MODEL_PATH", "/missing/path")
    provider = GemmaLocalProvider(model="/also/missing", candidate_roots=["/still/missing"])

    assert provider.health_check() is False
    assert "/missing/path" in provider._attempted_paths
