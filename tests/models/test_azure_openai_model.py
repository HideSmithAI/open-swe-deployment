from unittest.mock import patch

import pytest

from agent.dashboard.options import azure_model_option, resolve_default_model_id
from agent.utils import model


@pytest.fixture
def local_azure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHBOARD_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("LLM_MODEL_ID", "azure_openai:gpt-5.6-terra")
    monkeypatch.setenv("AZURE_API_KEY", "azure-key")
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://example.cognitiveservices.azure.com/",
    )
    monkeypatch.setenv("OPENAI_API_VERSION", "2024-12-01-preview")


def test_azure_model_option_reuses_known_openai_capabilities() -> None:
    option = azure_model_option(
        "azure_openai:gpt-5.6-terra",
        base_model="gpt-5.6-terra",
    )

    assert option == {
        "id": "azure_openai:gpt-5.6-terra",
        "label": "Azure GPT-5.6 Terra",
        "efforts": ["none"],
        "default_effort": "none",
        "supports_images": True,
    }


@pytest.mark.parametrize("model_id", [None, "", "openai:gpt-5.6-terra", "azure_openai:"])
def test_azure_model_option_rejects_non_azure_ids(model_id: str | None) -> None:
    assert azure_model_option(model_id) is None


def test_resolve_default_model_id_uses_configured_azure_model() -> None:
    supported = frozenset(
        {
            "openai:gpt-5.5",
            "openai:gpt-5.6-terra",
            "azure_openai:gpt-5.6-terra",
        }
    )

    assert (
        resolve_default_model_id(
            "azure_openai:gpt-5.6-terra",
            supported,
            fallback="openai:gpt-5.5",
        )
        == "azure_openai:gpt-5.6-terra"
    )
    assert (
        resolve_default_model_id("unknown:model", supported, fallback="openai:gpt-5.5")
        == "openai:gpt-5.5"
    )
    assert (
        resolve_default_model_id(
            "openai:gpt-5.6-terra",
            supported,
            fallback="openai:gpt-5.5",
        )
        == "openai:gpt-5.5"
    )


def test_make_model_wires_azure_foundry_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_API_KEY", "azure-key")
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://example.cognitiveservices.azure.com/",
    )
    monkeypatch.setenv("OPENAI_API_VERSION", "2024-12-01-preview")
    captured: dict[str, object] = {}

    def fake_init_chat_model(model: str, **kwargs: object) -> str:
        captured["model"] = model
        captured.update(kwargs)
        return "MODEL"

    with patch.object(model, "init_chat_model", fake_init_chat_model):
        result = model.make_model(
            "azure_openai:gpt-5.6-terra",
            use_gateway=False,
            max_tokens=16_384,
        )

    assert result == "MODEL"
    assert captured == {
        "model": "azure_openai:gpt-5.6-terra",
        "api_key": "azure-key",
        "azure_endpoint": "https://example.cognitiveservices.azure.com/",
        "api_version": "2024-12-01-preview",
        "max_retries": model.DEFAULT_MAX_RETRIES,
        "max_tokens": 16_384,
    }


def test_validate_local_azure_config_accepts_azure_api_key_alias(
    local_azure_env: None,
) -> None:
    model.validate_local_dev_llm_config()


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        ("key", "AZURE_OPENAI_API_KEY or AZURE_API_KEY"),
        ("endpoint", "AZURE_OPENAI_ENDPOINT"),
        ("version", "OPENAI_API_VERSION or AZURE_OPENAI_API_VERSION"),
    ],
)
def test_validate_local_azure_config_reports_missing_settings(
    monkeypatch: pytest.MonkeyPatch,
    local_azure_env: None,
    missing: str,
    message: str,
) -> None:
    if missing == "key":
        monkeypatch.delenv("AZURE_API_KEY")
    elif missing == "endpoint":
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT")
    else:
        monkeypatch.delenv("OPENAI_API_VERSION")

    with pytest.raises(ValueError, match=message):
        model.validate_local_dev_llm_config()
