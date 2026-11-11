"""
Terminal chat client for the AI Chatbot API.

Notice: THIS program keeps the conversation history, and sends ALL of it
with every request. The server and the model remember nothing (stateless).

Run (with the server running):  python chat_client.py
Add --stream to see tokens appear as they are generated.
"""

import sys
import httpx

API_URL = "http://localhost:8000"
STREAM = "--stream" in sys.argv


def main():
    history = []  # the chatbot's "memory" lives here, in the client
    print("Chat started. Type 'quit' to exit.\n")

    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in {"quit", "exit"}:
            break
        if not user_text:
            continue

        history.append({"role": "user", "content": user_text})
        payload = {"messages": history}

        try:
            if STREAM:
                print("Bot: ", end="", flush=True)
                reply = ""
                with httpx.stream("POST", f"{API_URL}/chat/stream", json=payload, timeout=120) as r:
                    r.raise_for_status()
                    for chunk in r.iter_text():
                        print(chunk, end="", flush=True)
                        reply += chunk
                print("\n")
            else:
                r = httpx.post(f"{API_URL}/chat", json=payload, timeout=120)
                r.raise_for_status()
                data = r.json()
                reply = data["reply"]
                print(f"Bot: {reply}")
                # Watch input tokens grow as the conversation gets longer!
                print(f"     [tokens in: {data['input_tokens']}, out: {data['output_tokens']}, "
                      f"messages sent: {data['messages_sent']}]\n")
        except httpx.HTTPStatusError as e:
            print(f"Error {e.response.status_code}: {e.response.text}\n")
            history.pop()  # drop the failed message so history stays valid
            continue
        except httpx.ConnectError:
            print("Can't reach the server. Is uvicorn running?\n")
            history.pop()
            continue

        history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
