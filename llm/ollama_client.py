import requests
from config import OLLAMA_URL, MODEL_NAME


def call_llm(prompt: str):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0
            }
        }
    )

    return response.json().get("response", "").strip()