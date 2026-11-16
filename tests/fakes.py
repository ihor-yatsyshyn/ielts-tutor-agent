"""FakeLLM для тестів: черга готових відповідей, жодних мережевих викликів."""
from agent.llm import LLMReply, ToolCall


class FakeLLM:
    def __init__(self, replies=None, json_objs=None):
        self.replies = list(replies or [])       # list[LLMReply]
        self.json_objs = list(json_objs or [])   # list[BaseModel | dict]
        self.chat_calls = []

    def chat(self, messages, tools=None, temperature=0.4, max_tokens=1500):
        self.chat_calls.append({"messages": messages, "tools": tools})
        return self.replies.pop(0) if self.replies else LLMReply(content="ok")

    def json_complete(self, system, user, model_cls, temperature=0.3, max_tokens=2500):
        obj = self.json_objs.pop(0)
        return obj if isinstance(obj, model_cls) else model_cls.model_validate(obj)


def tool_reply(name, args_json="{}", call_id="c1"):
    return LLMReply(content="", tool_calls=[ToolCall(call_id, name, args_json)])
