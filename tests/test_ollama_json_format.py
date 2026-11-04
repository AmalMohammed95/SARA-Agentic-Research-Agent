import json
from unittest.mock import patch
from sara.model import OllamaModelClient


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps({"response": "{}", "eval_count": 2}).encode()


def test_ollama_schema_sent_only_when_requested():
    seen = []

    def fake_open(request, timeout):
        seen.append(json.loads(request.data))
        return _Response()

    client = OllamaModelClient()
    with patch("sara.model.urllib.request.urlopen", side_effect=fake_open):
        client.generate("test")
        client.generate("test", format={"type": "object"})
    assert "format" not in seen[0]
    assert seen[1]["format"] == {"type": "object"}
