import os
from openai import OpenAI
from openai.types.completion import Completion


class Openai:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.chat_history = []
        self.prefix = ""

    def set_prefix(self, prefix) -> None:
        self.prefix = prefix

    def get_chat_history(self) -> list:
        return self.chat_history

    def chat(self, *, message: str, images: list = [], max_tokens: int = 100) -> Completion:
        """
        @param message: str, required
        @param images: list , default = [], No use for now
        @param max_tokens: int, default = 150
        """
        self.client.chat
        res: Completion = self.client.completions.create(
            model="gpt-4o-mini",
            max_tokens=max_tokens,
            message=[
                {"role": "system", "content": self.prefix},
                {"role": "user", "content": message},
            ],
        )
        self.chat_history.append(res)
        return res
