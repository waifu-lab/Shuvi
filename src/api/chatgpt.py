import os
from openai import OpenAI

class Openai:
    def __init__(self, api_key):
        self.api_key = api_key

        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
