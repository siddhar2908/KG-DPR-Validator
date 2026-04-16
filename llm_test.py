import requests

res = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3:8b",
        "prompt": "Return JSON: [{\"a\":1}]",
        "stream": False
    }
)

print(res.json()["response"])