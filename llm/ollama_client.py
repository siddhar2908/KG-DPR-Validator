import json
import requests
from config import OLLAMA_BASE_URL, MODEL_NAME, OLLAMA_TIMEOUT

GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"


def call_llm(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(
            GENERATE_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )

        if response.status_code != 200:
            print(f"❌ LLM HTTP {response.status_code}")
            try:
                print("❌ RESPONSE BODY:", response.text[:1000])
            except Exception:
                pass
            return ""

        result = response.json()
        return result.get("response", "").strip()

    except requests.RequestException as e:
        print(f"❌ LLM REQUEST ERROR: {e}")
        return ""
    except json.JSONDecodeError as e:
        print(f"❌ LLM JSON DECODE ERROR: {e}")
        return ""
    except Exception as e:
        print(f"❌ LLM ERROR: {e}")
        return ""