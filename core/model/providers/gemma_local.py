"""Gemma local provider using a local HuggingFace checkpoint."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import ClassVar, Iterator

import structlog

from core.model.base import Message, ModelOptions, ModelResponse

log = structlog.get_logger(__name__)


class GemmaLocalProvider:
    """Runs Gemma locally from a checkpoint directory."""

    name = "gemma4_local"

    # Class-level cache: model_path → loaded instance.
    # Prevents reloading the 26B model on every API request.
    _instances: ClassVar[dict[str, "GemmaLocalProvider"]] = {}

    @classmethod
    def get_or_create(cls, model: str, base_url: str = "") -> "GemmaLocalProvider":
        """Return a cached instance so the model is only loaded once per process."""
        if model not in cls._instances:
            cls._instances[model] = cls(model=model, base_url=base_url)
        return cls._instances[model]

    def __init__(
        self,
        model: str = "/mnt/raid1/CHK/playground/Gemma4/ckpts/gemma-4-26B-A4B-it",
        base_url: str = "",
        candidate_roots: list[str] | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self._model_path = Path(os.getenv("GEMMA_MODEL_PATH", model)).expanduser()
        self._candidate_roots = [Path(p).expanduser() for p in (candidate_roots or [])]
        self._resolved_model_path: Path | None = None
        self._attempted_paths: list[str] = []
        self._client = None
        self._tokenizer = None

    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_checkpoint_dir(path: Path) -> bool:
        has_config = (path / "config.json").exists()
        has_weights = any(path.glob("*.safetensors")) or any(path.glob("pytorch_model*.bin"))
        return has_config and has_weights

    @staticmethod
    def _size_rank(path: Path) -> int:
        match = re.search(r"(\d+)\s*[bB]", path.name)
        if not match:
            return -1
        return int(match.group(1))

    def _iter_candidate_roots(self) -> list[Path]:
        roots: list[Path] = []
        env_path = os.getenv("GEMMA_MODEL_PATH", "").strip()
        if env_path:
            roots.append(Path(env_path).expanduser())
        roots.append(self._model_path)
        roots.extend(self._candidate_roots)
        roots.extend(
            [
                Path("/mnt/raid1/CHK/playground/Gemma4/ckpts"),
                Path("/workspace/playground/Gemma4/ckpts"),
                Path("/home/a6000/CHK/playground/Gemma4/ckpts"),
            ]
        )
        deduped: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(root)
        return deduped

    def _pick_from_root(self, root: Path) -> Path | None:
        if not root.exists() or root.is_file():
            return None
        if self._is_valid_checkpoint_dir(root):
            return root
        candidates = [p for p in root.rglob("*") if p.is_dir() and self._is_valid_checkpoint_dir(p)]
        if not candidates:
            return None
        candidates.sort(key=self._size_rank, reverse=True)
        return candidates[0]

    def _resolve_model_path(self) -> Path | None:
        if self._resolved_model_path is not None:
            return self._resolved_model_path
        self._attempted_paths = []
        for root in self._iter_candidate_roots():
            self._attempted_paths.append(str(root))
            picked = self._pick_from_root(root)
            if picked is not None:
                self._resolved_model_path = picked
                return picked
        return None

    def _ensure_loaded(self) -> None:
        if self._client is not None and self._tokenizer is not None:
            return
        resolved = self._resolve_model_path()
        if resolved is None or not self.health_check():
            raise RuntimeError(
                f"Gemma checkpoint not available: {self._model_path}. "
                f"Attempted paths: {self._attempted_paths}. "
                "Set GEMMA_MODEL_PATH to a valid local model directory."
            )
        try:
            import torch  # type: ignore[import]
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore[import]
        except Exception as exc:
            raise RuntimeError(
                "Gemma local backend requires transformers and torch to be installed."
            ) from exc

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(str(resolved), trust_remote_code=True)
            self._client = AutoModelForCausalLM.from_pretrained(
                str(resolved),
                trust_remote_code=True,
                torch_dtype="auto",
                device_map="auto",
            )
            self._client.eval()
            log.info("gemma_local.model_loaded", model_path=str(resolved))
        except Exception as exc:
            raise RuntimeError(f"Failed to load Gemma model from {resolved}: {exc}") from exc

    def complete(self, messages: list[Message], options: ModelOptions | None = None) -> ModelResponse:
        self._ensure_loaded()
        assert self._client is not None and self._tokenizer is not None
        resolved = self._resolve_model_path()
        assert resolved is not None

        import torch  # type: ignore[import]

        opts = options or ModelOptions()
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        model_device = next(self._client.parameters()).device
        inputs = {k: v.to(model_device) for k, v in inputs.items()}

        with torch.no_grad():
            generated = self._client.generate(
                **inputs,
                max_new_tokens=opts.max_tokens,
                temperature=opts.temperature,
                do_sample=opts.temperature > 0,
            )
        output_ids = generated[0][inputs["input_ids"].shape[-1]:]
        content = self._tokenizer.decode(output_ids, skip_special_tokens=True)

        return ModelResponse(
            content=content,
            model=str(resolved),
            provider=self.name,
        )

    def stream(self, messages: list[Message], options: ModelOptions | None = None) -> Iterator[str]:
        # Keep interface contract; for V1 we generate once and yield a single chunk.
        response = self.complete(messages, options)
        yield response.content

    def health_check(self) -> bool:
        try:
            resolved = self._resolve_model_path()
            if resolved is None:
                log.warning(
                    "gemma_local.health_check_failed",
                    error=f"no_valid_checkpoint_under:{self._model_path} attempted={self._attempted_paths}",
                )
                return False
            return True
        except Exception as exc:
            log.warning("gemma_local.health_check_failed", error=str(exc))
            return False
