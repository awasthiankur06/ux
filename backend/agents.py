import os
import json
import logging
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
logger = logging.getLogger(__name__)


def _redact_headers(headers: dict) -> dict:
    return {
        key: "****" if key.lower() in {"api-key", "authorization", "x-api-key", "cookie", "set-cookie"} else value
        for key, value in headers.items()
    }


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
        api_version = provider_config.get("api_version") or os.environ.get("EY_INCUBATOR_API_VERSION")
        if not base_url:
            raise RuntimeError("EY Incubator endpoint is not configured. Add it in Agent Inventory > LLM Settings.")
        if not api_key:
            raise RuntimeError("EY Incubator API key is not configured. Add it in Agent Inventory > LLM Settings.")
        if not api_version:
            raise RuntimeError("EY Incubator API version is not configured. Add it in Agent Inventory > LLM Settings.")

        url = f"{base_url}/openai/deployments/{model}/chat/completions"
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
        }
        logger.info(
            "EY_INCUBATOR_REQUEST %s",
            json.dumps({"method": "POST", "url": url, "params": {"api-version": api_version}, "headers": _redact_headers(headers), "payload": payload}),
        )
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                params={"api-version": api_version},
                headers=headers,
                json=payload,
            )
        logger.info(
            "EY_INCUBATOR_RESPONSE %s",
            json.dumps({"status_code": response.status_code, "headers": _redact_headers(dict(response.headers)), "body": response.text}),
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
