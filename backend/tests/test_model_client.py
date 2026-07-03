import httpx
import pytest

from backend.app.services.model_client import ChatMessage, ModelClient


@pytest.mark.asyncio
async def test_model_client_posts_chat_completion():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["json"] = request.read().decode()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "中文回答"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = ModelClient(
        base_url="https://api.example.test/v1",
        api_key="key-123",
        model="demo-model",
        timeout_seconds=30,
        temperature=0.2,
        transport=transport,
    )

    result = await client.complete(messages=[ChatMessage(role="user", content="hello")])

    assert result == "中文回答"
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["auth"] == "Bearer key-123"
    assert '"model":"demo-model"' in captured["json"].replace(" ", "")


@pytest.mark.asyncio
async def test_model_client_accepts_full_chat_completions_url():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = ModelClient(
        base_url="https://openrouter.ai/api/v1/chat/completions",
        api_key="key-123",
        model="openai/gpt-5.4",
        timeout_seconds=30,
        temperature=0.2,
        transport=transport,
    )

    await client.complete(messages=[ChatMessage(role="user", content="hello")])

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
