"""Адаптер LLM (Groq). Решта коду залежить лише від інтерфейсу LLM (chat/json_complete)."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

import config
from errors import LLMError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # сирий JSON-рядок


@dataclass
class LLMReply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM(Protocol):
    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             temperature: float = 0.4, max_tokens: int = 1500) -> LLMReply: ...

    def json_complete(self, system: str, user: str, model_cls: type[T],
                      temperature: float = 0.3, max_tokens: int = 2500) -> T: ...


class GroqLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        from groq import Groq
        self.model = model or config.GROQ_MODEL
        key = api_key or config.GROQ_API_KEY
        if not key:
            raise LLMError("GROQ_API_KEY не налаштований (див. README).", "CONFIG_ERROR", False)
        self.client = Groq(api_key=key, timeout=config.LLM_TIMEOUT_SECONDS, max_retries=0)

    def _call(self, **kwargs):
        import groq
        last = None
        for i in range(config.LLM_MAX_RETRIES + 1):
            try:
                return self.client.chat.completions.create(model=self.model, **kwargs)
            except (groq.APIConnectionError, groq.RateLimitError) as e:  # включно з timeout
                last = e
                log.warning("Groq transient error (%s), retry %s", type(e).__name__, i + 1)
                time.sleep(2 ** i)
            except groq.APIStatusError as e:
                raise LLMError(f"Помилка LLM API ({e.status_code}).", "LLM_ERROR",
                               retryable=e.status_code >= 500) from e
        raise LLMError("LLM не відповів вчасно. Спробуйте ще раз.", "LLM_TIMEOUT") from last

    def chat(self, messages, tools=None, temperature=0.4, max_tokens=1500) -> LLMReply:
        kwargs = dict(messages=messages, temperature=temperature, max_tokens=max_tokens)
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        msg = self._call(**kwargs).choices[0].message
        calls = [ToolCall(c.id, c.function.name, c.function.arguments or "{}")
                 for c in (msg.tool_calls or [])]
        return LLMReply(content=msg.content or "", tool_calls=calls)

    def json_complete(self, system, user, model_cls, temperature=0.3, max_tokens=2500):
        schema = json.dumps(model_cls.model_json_schema(), ensure_ascii=False)
        msgs = [{"role": "system", "content": f"{system}\n\nReturn ONLY a valid JSON object "
                                              f"matching this JSON schema:\n{schema}"},
                {"role": "user", "content": user}]
        for _ in range(2):  # одна спроба «ремонту»
            resp = self._call(messages=msgs, temperature=temperature, max_tokens=max_tokens,
                              response_format={"type": "json_object"})
            raw = resp.choices[0].message.content or ""
            try:
                return model_cls.model_validate_json(raw)
            except (ValidationError, ValueError) as e:
                msgs += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": f"Invalid JSON/schema: {str(e)[:500]}. "
                                                     "Return corrected JSON only."}]
        raise LLMError("Модель повернула невалідну структуру. Спробуйте ще раз.", "LLM_ERROR")


_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = GroqLLM()
    return _llm


def set_llm(llm: LLM | None) -> None:
    """Підміна (тести / dependency injection)."""
    global _llm
    _llm = llm
