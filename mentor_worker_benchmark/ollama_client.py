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
            "Ollama server is not running. Start the Ollama desktop app or run `ollama serve`.",
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
        try:
            response = requests.get(self._url("/api/tags"), timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                "Failed to query local models. Ensure Ollama is running at http://localhost:11434."
            ) from exc

        payload = response.json()
        models = payload.get("models", [])
        names: set[str] = set()
        for item in models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.add(item["name"])
        return names

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
    ) -> str:
        request_messages = list(messages)
        if system:
            request_messages = [{"role": "system", "content": system}] + request_messages

        payload: dict[str, Any] = {
            "model": model,
            "messages": request_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }

        try:
            response = requests.post(
                self._url("/api/chat"),
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Ollama chat request failed for model `{model}`. Ensure the model is available and server is healthy."
            ) from exc

        body = response.json()
        message = body.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"Unexpected Ollama response format for model `{model}`: {body}")
        return content
