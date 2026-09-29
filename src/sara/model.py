"""
Model boundary for SARA.

This module defines a provider-neutral interface for language models.
The rest of the SARA system should interact with ModelClient rather
than depending directly on a specific model provider.
"""

from abc import ABC, abstractmethod
import json
import urllib.request
import urllib.error


class ModelClient(ABC):
    """
    Abstract interface for language model providers.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a text response from a language model.

        Args:
            prompt: The prompt sent to the model.

        Returns:
            The model's text response.
        """
        pass


class OllamaModelClient(ModelClient):
    """
    Local Ollama implementation of the SARA model interface.
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str) -> str:
        """
        Generate a response using a locally running Ollama model.
        """

        if not prompt or not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        payload = {
            "model": self.model,
            "prompt": prompt.strip(),
            "stream": False,
        }

        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))

        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Unable to connect to Ollama: {error}"
            ) from error

        model_response = data.get("response", "").strip()

        if not model_response:
            raise RuntimeError("Ollama returned an empty response.")

        return model_response