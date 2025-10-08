import sys
import types
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _ensure_stub_module(name, **attributes):
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    for attr, value in attributes.items():
        setattr(module, attr, value)
    sys.modules[name] = module


class _StubAnthropic:  # pragma: no cover - simple stub
    def __init__(self, *args, **kwargs):
        self.messages = types.SimpleNamespace(create=lambda *a, **k: types.SimpleNamespace(content=[types.SimpleNamespace(text="")]))


class _StubOpenAI:  # pragma: no cover - simple stub
    def __init__(self, *args, **kwargs):
        self.responses = types.SimpleNamespace(create=lambda *a, **k: types.SimpleNamespace(model_dump=lambda: {}, output_text=""))
        self.images = types.SimpleNamespace(generate=lambda *a, **k: types.SimpleNamespace(data=[types.SimpleNamespace(b64_json="")]))


_ensure_stub_module("replicate", run=lambda *args, **kwargs: [])
_ensure_stub_module("together", Together=type("Together", (), {}))
_ensure_stub_module("anthropic", Anthropic=_StubAnthropic)
_ensure_stub_module("openai", OpenAI=_StubOpenAI)

import shared_utils


class ProviderUtilitiesTests(unittest.TestCase):
    def setUp(self):
        self.base_payload = {
            "prompt": "Hello",
            "context_messages": [],
            "full_messages": [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "Hello"}
            ],
            "model_id": "test-model",
            "system_prompt": "sys",
            "options": {},
            "fallback_provider": None,
            "fallback_model": None,
            "metadata": {}
        }

    def test_normalize_response_from_string(self):
        result = shared_utils.normalize_response("test response")
        self.assertEqual(result["content"], "test response")
        self.assertEqual(result["role"], "assistant")

    def test_invoke_provider_defaults_to_openrouter(self):
        payload = dict(self.base_payload)
        with patch.object(shared_utils, "call_openrouter_api", return_value="ok") as mock_openrouter:
            response = shared_utils.invoke_provider(None, payload)

        self.assertEqual(response["content"], "ok")
        self.assertEqual(response["provider"], "openrouter")
        mock_openrouter.assert_called_once()

    def test_deepseek_falls_back_to_legacy_handler(self):
        payload = dict(self.base_payload)
        payload.update({
            "fallback_provider": "deepseek_legacy",
            "fallback_model": "deepseek-ai/deepseek-r1"
        })

        def failing_handler(_payload):
            return {"role": "system", "content": "Error: official outage"}

        def legacy_handler(_payload):
            return "legacy recovered"

        with patch.dict(
            shared_utils.PROVIDER_REGISTRY,
            {
                "deepseek": {"handler": failing_handler, "supports_reasoning": True},
                "deepseek_legacy": {"handler": legacy_handler, "supports_reasoning": True}
            },
            clear=True
        ):
            with patch.object(shared_utils, "call_openrouter_api") as mock_openrouter:
                response = shared_utils.invoke_provider("deepseek", payload)

        self.assertEqual(response["content"], "legacy recovered")
        self.assertEqual(response["provider"], "deepseek_legacy")
        mock_openrouter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
