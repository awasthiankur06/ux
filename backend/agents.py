import os
import json
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


def _parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        if start == -1:
            start = text.find("[")
        if start == -1:
            raise
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj


async def run_llm_agent(system_prompt: str, provider: str, model: str, user_text: str, session_id: str, settings: dict | None = None) -> str:
    if provider == "ey_incubator":
        provider_config = ((settings or {}).get("provider_configs") or {}).get("ey_incubator") or {}
        base_url = (provider_config.get("base_url") or os.environ.get("EY_INCUBATOR_BASE_URL") or "").rstrip("/")
        api_key = ((settings or {}).get("api_keys") or {}).get("ey_incubator") or os.environ.get("EY_INCUBATOR_API_KEY")
        if not base_url:
            raise RuntimeError("EY Incubator endpoint is not configured. Add it in Agent Inventory > LLM Settings.")
        if not api_key:
            raise RuntimeError("EY Incubator API key is not configured. Add it in Agent Inventory > LLM Settings.")
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text},
                    ],
                },
            )
        response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("EY Incubator returned an unexpected Chat Completions response.") from error
        if not content:
            raise RuntimeError("EY Incubator returned an empty response.")
        return content

    api_key = ((settings or {}).get("api_keys") or {}).get(provider) or EMERGENT_LLM_KEY
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(provider, model)
    return await chat.send_message(UserMessage(text=user_text))
