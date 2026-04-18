from llm.ollama_client import call_llm

print(call_llm("Give me JSON: [{\"a\":1}]"))