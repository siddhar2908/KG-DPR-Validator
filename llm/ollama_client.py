import requests
from config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT

GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"


def _call(prompt: str, model_name: str) -> str:
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.05},
    }
    response = requests.post(GENERATE_URL, json=payload, timeout=OLLAMA_TIMEOUT)
    if response.status_code != 200:
        body = ""
        try:
            body = response.text[:1000]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {response.status_code}: {body}")
    result = response.json()
    return result.get("response", "").strip()


def call_llm(prompt: str, model_name: str, fallback_model: str = "llama3:8b") -> str:
    try:
        return _call(prompt, model_name)
    except Exception as e:
        print(f"❌ Primary model failed [{model_name}]: {e}")
        if fallback_model and fallback_model != model_name:
            try:
                print(f"🔁 Retrying with fallback model [{fallback_model}]")
                return _call(prompt, fallback_model)
            except Exception as e2:
                print(f"❌ Fallback model failed [{fallback_model}]: {e2}")
        return ""
