from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class OllamaServerStatus:
    reachable: bool
    message: str


class OllamaClient:
    """Minimal Ollama API client for deterministic local chat completions."""

    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", timeout_seconds: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def is_server_reachable(self) -> bool:
        try:
            response = requests.get(self._url("/api/tags"), timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def ensure_server_running(self, auto_start: bool = True) -> OllamaServerStatus:
        if self.is_server_reachable():
            return OllamaServerStatus(True, "Ollama server is reachable.")

        if not self.is_ollama_installed():
            return OllamaServerStatus(
                False,
                "Ollama is not installed. Install it from https://ollama.com/download and re-run setup.",
            )

        if auto_start:
            # Best-effort startup for CLI environments.
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            for _ in range(8):
                time.sleep(1)
                if self.is_server_reachable():
                    return OllamaServerStatus(True, "Started Ollama server with `ollama serve`.")

        return OllamaServerStatus(
            False,
            (
                "Ollama server is not running. Start the Ollama desktop app, "
                "or run `ollama serve` in a separate terminal, then retry."
            ),
        )

    @staticmethod
    def is_ollama_installed() -> bool:
        try:
            subprocess.run(
                ["ollama", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return True
        except (OSError, subprocess.CalledProcessError):
            return False

    def list_local_models(self) -> set[str]:
        catalog = self.get_model_catalog()
        names: set[str] = set()
        for item in catalog:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.add(item["name"])
        return names

    def get_model_catalog(self) -> list[dict[str, Any]]:
        try:
            response = requests.get(self._url("/api/tags"), timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                "Failed to query local models at http://localhost:11434. "
                "Start Ollama Desktop or run `ollama serve`, then retry."
            ) from exc

        payload = response.json()
        models = payload.get("models", [])
        if not isinstance(models, list):
            return []
        return [item for item in models if isinstance(item, dict)]

    def get_model_details(self, model_names: list[str]) -> list[dict[str, Any]]:
        by_name = {str(item.get("name")): item for item in self.get_model_catalog()}
        details: list[dict[str, Any]] = []
        for model_name in model_names:
            if model_name in by_name:
                details.append(by_name[model_name])
            else:
                details.append({"name": model_name, "missing": True})
        return details

    @staticmethod
    def get_ollama_version() -> str | None:
        try:
            process = subprocess.run(
                ["ollama", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return process.stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    def pull_model(self, model: str) -> None:
        process = subprocess.run(
            ["ollama", "pull", model],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if process.returncode != 0:
            raise RuntimeError(f"Failed to pull model `{model}`:\n{process.stdout}")

    def ensure_models(self, models: list[str]) -> list[str]:
        local_models = self.list_local_models()
        pulled: list[str] = []
        for model in models:
            if model not in local_models:
                self.pull_model(model)
                pulled.append(model)
        return pulled

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        system: str | None = None,
        temperature: float = 0.0,
        top_p: float = 1.0,
        num_predict: int = 512,
        seed: int | None = None,
    ) -> str:
        request_messages = list(messages)
        if system:
            request_messages = [{"role": "system", "content": system}] + request_messages

        options: dict[str, Any] = {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": num_predict,
        }
        if seed is not None:
            options["seed"] = seed

        payload: dict[str, Any] = {
            "model": model,
            "messages": request_messages,
            "stream": False,
            "options": options,
        }

        try:
            request_timeout: tuple[int, int] = (5, max(10, self.timeout_seconds * 3))
            response = requests.post(
                self._url("/api/chat"),
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=request_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Ollama chat request failed for model `{model}`. "
                "Confirm Ollama is running (`ollama serve`) and the model is pulled (`ollama list`)."
            ) from exc

        body = response.json()
        message = body.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"Unexpected Ollama response format for model `{model}`: {body}")
        return content

    def runtime_metadata(self, model_names: list[str]) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "cli_version": self.get_ollama_version(),
            "model_tags": self.get_model_details(model_names),
        }
