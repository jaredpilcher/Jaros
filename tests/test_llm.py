"""Tests for the Interchangeable LLM Adapter (EXT-004)."""

from __future__ import annotations

import dataclasses
import json

import pytest

from jaros.llm import (
    LlmClient,
    LlmConfig,
    LlmRequest,
    LlmResponse,
    create_llm_client,
)


def _run_via_client(client: LlmClient, prompt: str) -> LlmResponse:
    """A single, provider-agnostic call site depending only on LlmClient."""
    return client.complete(LlmRequest(prompt=prompt))


def test_default_provider_works():
    client = create_llm_client({"provider": "default"})
    assert isinstance(client, LlmClient)
    resp = _run_via_client(client, "hello")
    assert resp.text == "hello"
    assert resp.model == "default-echo"


def test_uppercase_provider_works():
    client = create_llm_client(LlmConfig(provider="uppercase"))
    assert isinstance(client, LlmClient)
    resp = _run_via_client(client, "hello")
    assert resp.text == "HELLO"
    assert resp.model == "uppercase-echo"


def test_unknown_provider_raises_listing_known():
    with pytest.raises(ValueError) as exc:
        create_llm_client({"provider": "nope"})
    msg = str(exc.value)
    assert "nope" in msg
    # The error lists the known providers to make misconfiguration obvious.
    assert "default" in msg and "uppercase" in msg


def test_missing_provider_key_raises():
    with pytest.raises(ValueError):
        create_llm_client({})


def test_swap_provider_changes_output_with_no_caller_change():
    """Same call site; only configuration differs -> different output."""
    prompt = "Swap Me"
    out_default = _run_via_client(create_llm_client({"provider": "default"}), prompt)
    out_upper = _run_via_client(create_llm_client({"provider": "uppercase"}), prompt)
    assert out_default.text == "Swap Me"
    assert out_upper.text == "SWAP ME"
    # Identical call site, different model -> proves a config-only swap.
    assert out_default.text != out_upper.text


def test_response_is_data_only_json_round_trips():
    client = create_llm_client({"provider": "default"})
    resp = client.complete(LlmRequest(prompt="data only", params={"temperature": 0}))
    as_dict = dataclasses.asdict(resp)
    # No callables/handles anywhere; the whole response JSON round-trips.
    assert json.loads(json.dumps(as_dict)) == as_dict


def test_response_holds_no_callables():
    resp = create_llm_client({"provider": "default"}).complete(LlmRequest(prompt="x"))
    for value in dataclasses.asdict(resp).values():
        assert not callable(value)


def test_response_is_frozen_immutable():
    resp = LlmResponse(text="t", model="m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        resp.text = "other"  # type: ignore[misc]


def test_ollama_provider_works():
    from unittest.mock import MagicMock, patch

    mock_response = MagicMock()
    mock_response.read.return_value = b'{"response": "mocked ollama output"}'
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        with patch.dict("os.environ", {"OLLAMA_HOST": "http://localhost:11434", "OLLAMA_MODEL": "llama3"}):
            client = create_llm_client({"provider": "ollama"})
            assert isinstance(client, LlmClient)
            resp = _run_via_client(client, "hello")
            assert resp.text == "mocked ollama output"
            assert resp.model == "llama3"

        mock_urlopen.assert_called_once()
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.full_url == "http://localhost:11434/api/generate"
        assert req_arg.get_method() == "POST"
