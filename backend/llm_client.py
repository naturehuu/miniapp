import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests


PROVIDER_CONFIG = {
    "openai": {
        "key_env": "OPENAI_API_KEY",
        "base_env": "OPENAI_BASE_URL",
        "model_env": "OPENAI_MODEL",
    },
    "deepseek": {
        "key_env": "DEEPSEEK_API_KEY",
        "base_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
    },
    "qwen": {
        "key_env": "QWEN_API_KEY",
        "base_env": "QWEN_BASE_URL",
        "model_env": "QWEN_MODEL",
    },
    "hunyuan": {
        "key_env": "HUNYUAN_API_KEY",
        "base_env": "HUNYUAN_BASE_URL",
        "model_env": "HUNYUAN_MODEL",
    },
}


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
        self.last_error: str = ""
        self.logger = logging.getLogger("llm")
        self.connect_timeout = float(os.getenv("LLM_CONNECT_TIMEOUT", "10"))
        self.read_timeout = float(os.getenv("LLM_READ_TIMEOUT", "90"))
        self.max_retries = max(0, int(os.getenv("LLM_MAX_RETRIES", "1")))
        self.default_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "800"))
        self.default_temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.qwen_enable_thinking = self._env_bool("QWEN_ENABLE_THINKING", False)

    def available(self) -> bool:
        if self.provider == "mock":
            return False
        if self.provider not in PROVIDER_CONFIG:
            return False
        config = PROVIDER_CONFIG[self.provider]
        return bool(os.getenv(config["key_env"], "").strip())

    def _get_config(self) -> Dict[str, str]:
        config = PROVIDER_CONFIG[self.provider]
        api_key = os.getenv(config["key_env"], "").strip()
        base_url = os.getenv(config["base_env"], "").strip().rstrip("/")
        model = os.getenv(config["model_env"], "").strip()
        return {"api_key": api_key, "base_url": base_url, "model": model}

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: Optional[int] = None,
        enable_thinking: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.available():
            self.last_error = "provider unavailable or api key missing"
            self.logger.warning("LLM unavailable: provider=%s", self.provider)
            return None

        cfg = self._get_config()
        url = f"{cfg['base_url']}/chat/completions"
        masked_key = self._mask_secret(cfg["api_key"])
        self.logger.info(
            "LLM request start: provider=%s model=%s url=%s key=%s timeout=(%ss,%ss) retries=%s",
            self.provider,
            cfg["model"],
            url,
            masked_key,
            self.connect_timeout,
            self.read_timeout,
            self.max_retries,
        )
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
        }
        # Some compatible APIs do not support response_format.
        if self.provider in {"openai", "deepseek"}:
            payload["response_format"] = {"type": "json_object"}
        if self.provider == "qwen":
            thinking = self.qwen_enable_thinking if enable_thinking is None else enable_thinking
            payload["extra_body"] = {"enable_thinking": thinking}
        self.logger.info(
            "LLM request params: provider=%s max_tokens=%s temperature=%s qwen_enable_thinking=%s",
            self.provider,
            payload.get("max_tokens"),
            payload.get("temperature"),
            payload.get("extra_body", {}).get("enable_thinking"),
        )
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=(self.connect_timeout, self.read_timeout),
                )
                resp.raise_for_status()
                data = resp.json()
                self.logger.info(
                    "LLM request success: provider=%s status=%s request_id=%s attempt=%s",
                    self.provider,
                    resp.status_code,
                    resp.headers.get("x-request-id")
                    or resp.headers.get("x-dashscope-request-id")
                    or "-",
                    attempt + 1,
                )
                content = data["choices"][0]["message"]["content"]
                text = self._message_to_text(content)
                if not text:
                    self.last_error = "empty model content"
                    self.logger.error("LLM empty content: provider=%s", self.provider)
                    return None
                parsed = self._parse_json_text(text)
                if parsed is None:
                    self.last_error = "model returned non-json content"
                    self.logger.error(
                        "LLM non-json content: provider=%s content_preview=%s",
                        self.provider,
                        text[:200],
                    )
                    return None
                self.last_error = ""
                return parsed
            except requests.HTTPError as e:
                resp = e.response
                status = resp.status_code if resp is not None else "unknown"
                req_id = "-"
                body_preview = ""
                if resp is not None:
                    req_id = (
                        resp.headers.get("x-request-id")
                        or resp.headers.get("x-dashscope-request-id")
                        or "-"
                    )
                    body_preview = (resp.text or "")[:500]
                self.last_error = f"http {status}, request_id={req_id}"
                self.logger.error(
                    "LLM HTTP error: provider=%s status=%s request_id=%s attempt=%s body=%s",
                    self.provider,
                    status,
                    req_id,
                    attempt + 1,
                    body_preview,
                )
                return None
            except requests.Timeout as e:
                self.last_error = f"timeout(connect={self.connect_timeout},read={self.read_timeout})"
                self.logger.warning(
                    "LLM timeout: provider=%s attempt=%s/%s error=%s",
                    self.provider,
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                )
                if attempt >= self.max_retries:
                    self.logger.error("LLM timeout exhausted: provider=%s", self.provider)
                    return None
                continue
            except Exception as e:
                self.last_error = str(e)
                self.logger.exception(
                    "LLM unexpected error: provider=%s attempt=%s error=%s",
                    self.provider,
                    attempt + 1,
                    e,
                )
                return None
        return None

    def _message_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    text = str(part.get("text", "")).strip()
                    if text:
                        parts.append(text)
            return "\n".join(parts).strip()
        return ""

    def _parse_json_text(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except Exception:
            pass

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except Exception:
                return None
        return None

    def _mask_secret(self, value: str) -> str:
        if not value:
            return "<empty>"
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}***{value[-4:]}"

    def _env_bool(self, key: str, default: bool) -> bool:
        value = os.getenv(key, "").strip().lower()
        if not value:
            return default
        return value in {"1", "true", "yes", "on"}


def normalize_answers(
    answers: List[dict], questions: List[dict]
) -> List[Dict[str, str]]:
    question_map = {q["id"]: q["text"] for q in questions}
    normalized = []
    for item in answers:
        qid = str(item.get("question_id", "")).strip()
        ans = str(item.get("answer", "")).strip()
        if not qid:
            continue
        normalized.append(
            {
                "question_id": qid,
                "question_text": question_map.get(qid, ""),
                "answer": ans,
            }
        )
    return normalized
