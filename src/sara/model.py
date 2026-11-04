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
import time
import os
import hashlib


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
        self._response_cache = {}
        self._cache_limit = 128

    def generate(self, prompt: str, *, format=None) -> str:
        """
        Generate a response using a locally running Ollama model.
        """

        if not prompt or not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        # Exact-prompt in-memory cache avoids repeated expensive local inference.
        # It is scoped to this client instance and never written to disk.
        cache_key = hashlib.sha256(json.dumps(
            [self.model, prompt.strip(), format], sort_keys=True,
            ensure_ascii=False).encode('utf-8')).hexdigest()
        if os.getenv('SARA_MODEL_CACHE', '1') == '1' and cache_key in self._response_cache:
            return self._response_cache[cache_key]

        payload = {
        "model": self.model,
        "prompt": prompt.strip(),
        "stream": False,
        "keep_alive": "30m",
        }

        if format is not None:
            payload["format"] = format
        # Optional generation cap; disabled by default to avoid truncated JSON.
        token_cap = os.getenv('SARA_MAX_OUTPUT_TOKENS', '').strip()
        if token_cap.isdigit() and int(token_cap) > 0:
            payload['options'] = {'num_predict': min(int(token_cap), 8192)}

        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start_time = time.perf_counter()

        try:
            with urllib.request.urlopen(request, timeout=max(5, min(600, int(os.getenv('SARA_OLLAMA_TIMEOUT', '120'))))) as response:
                data = json.loads(response.read().decode("utf-8"))

            elapsed = time.perf_counter() - start_time

            print(
                f"[OLLAMA] duration={elapsed:.2f}s "
                f"prompt_chars={len(prompt)} "
                f"response_chars={len(data.get('response', ''))} "
                f"eval_count={data.get('eval_count', 'N/A')} "
                f"prompt_eval_count={data.get('prompt_eval_count', 'N/A')} "
                f"prompt_eval_duration_ns={data.get('prompt_eval_duration', 'N/A')} "
                f"eval_duration_ns={data.get('eval_duration', 'N/A')} "
                f"load_duration_ns={data.get('load_duration', 'N/A')}",
                flush=True,
            )

        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Unable to connect to Ollama: {error}"
            ) from error

        model_response = data.get("response", "").strip()

        if not model_response:
            raise RuntimeError("Ollama returned an empty response.")

        if os.getenv('SARA_MODEL_CACHE', '1') == '1':
            if len(self._response_cache) >= self._cache_limit:
                self._response_cache.pop(next(iter(self._response_cache)))
            self._response_cache[cache_key] = model_response
        return model_response

class GeminiModelClient(ModelClient):
    """
    Google Gemini implementation of the SARA model interface.
    """

    def __init__(self, model: str = "gemini-3.1-flash-lite"):
        import os
        from google import genai
        from google.genai import errors
        self._server_error_type = errors.ServerError

        if not os.environ.get("GEMINI_API_KEY"):
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set."
            )

        self.model = model
        self.client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"]
        )


    def generate(self, prompt: str) -> str:
        """
        Generate a response using Gemini API.
        Retry temporary server failures with bounded backoff.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt.strip(),
                )

                model_response = (response.text or "").strip()

                if not model_response:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return model_response

            except self._server_error_type as error:
                if error.code not in (500, 502, 503, 504):
                    raise

                if attempt == max_attempts - 1:
                    raise RuntimeError(
                        f"Gemini unavailable after {max_attempts} attempts."
                    ) from error

                wait_seconds = 2 ** (attempt + 1)
                print(
                    f"Gemini temporary error {error.code}. "
                    f"Retrying in {wait_seconds} seconds..."
                )
                time.sleep(wait_seconds)
