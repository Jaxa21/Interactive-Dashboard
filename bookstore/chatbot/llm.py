import json
from dataclasses import dataclass

from google import genai
from google.genai import types


@dataclass
class ToolCall:
    name: str
    args: dict
    result: dict


@dataclass
class Reply:
    text: str
    tool_calls: list


def find_tool_calls(history):
    waiting = []
    calls = []
    for content in history:
        for part in content.parts or []:
            if part.function_call:
                waiting.append(part.function_call)
            elif part.function_response:
                name = part.function_response.name
                args = {}
                for call in waiting:
                    if call.name == name:
                        args = dict(call.args or {})
                        waiting.remove(call)
                        break
                calls.append(ToolCall(name, args, part.function_response.response))
    return calls


class GeminiChat:
    def __init__(self, chat):
        self.chat = chat

    def send(self, message):
        start = len(self.chat.get_history())
        response = self.chat.send_message(message)
        history = self.chat.get_history()[start:]
        return Reply(response.text or "", find_tool_calls(history))


class GeminiJsonModel:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def ask_json(self, prompt):
        config = types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
        response = self.client.models.generate_content(model=self.model, contents=prompt, config=config)
        return json.loads(response.text or "{}")


class GeminiProvider:
    def __init__(self, api_key, model, max_tool_calls):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.max_tool_calls = max_tool_calls

    def chat(self, instructions, tools):
        calling = types.AutomaticFunctionCallingConfig(maximum_remote_calls=self.max_tool_calls)
        config = types.GenerateContentConfig(system_instruction=instructions, temperature=0, tools=tools,
                                             automatic_function_calling=calling)
        return GeminiChat(self.client.chats.create(model=self.model, config=config))

    def json_model(self):
        return GeminiJsonModel(self.client, self.model)
