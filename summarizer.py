import requests
from config import OLLAMA_URL, OLLAMA_MODEL

def summarize_with_ollama(context: str, question: str) -> str:
    """Send a summarization prompt to the local Ollama instance."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant summarizing lecture content."},
            {"role": "user", "content": f"Here's what the video said:\n\n{context}\n\nNow, answer this question as clearly as possible:\n{question}"}
        ],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        if "message" in data and "content" in data["message"]:
            return data["message"]["content"].strip()
        elif "response" in data:
            return data["response"].strip()
        else:
            return f"(Unexpected format: {data})"

    except Exception as e:
        return f"(Failed to summarize using Ollama: {e})"
