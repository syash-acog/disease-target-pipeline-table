import os
import requests
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self, base_url=None, username=None, password=None, model=None):
        self.base_url = base_url or "https://ollama.own1.aganitha.ai"
        self.username = username or os.getenv("username")
        self.password = password or os.getenv("password")
        self.model = model or "gemma3:27b"  # <-- Specify your model here

        self.session = requests.Session()
        self.session.auth = (self.username, self.password)

    def extract_drugs(self, prompt):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": "",
            "stream": False,
            "options": {}
        }
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")