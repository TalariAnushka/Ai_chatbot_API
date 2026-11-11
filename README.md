\# AI Chatbot API



A production-style REST API for a conversational AI chatbot, built with \*\*FastAPI\*\* and served by fast open-weight LLMs on \*\*Groq\*\*. It supports multi-turn conversations, real-time streaming, input validation, context-window management and clear error handling.



!\[Python](https://img.shields.io/badge/Python-3.11-blue)

!\[FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688)

!\[License](https://img.shields.io/badge/License-MIT-green)



\## Features



\- \*\*Multi-turn chat\*\*: `POST /chat` takes the full conversation and returns the reply with token usage.

\- \*\*Streaming responses\*\*: `POST /chat/stream` sends text as it is generated, for a faster-feeling UI.

\- \*\*Context management\*\*: only the most recent messages are sent to the model, keeping cost and latency under control.

\- \*\*Input validation\*\*: Pydantic schemas reject malformed requests with a `422` before any model call is made.

\- \*\*Clear error handling\*\*: provider failures are mapped to meaningful HTTP status codes (`400`, `429`, `502`, `503`).

\- \*\*Configurable\*\*: model, history length and system prompt are set through environment variables, so the model can be swapped without code changes.

\- \*\*Interactive docs\*\*: auto-generated Swagger UI at `/docs`.

\- \*\*Terminal client\*\*: a small CLI client for chatting with the API, with optional streaming.



\## Architecture



```mermaid

flowchart LR

&#x20;   C\[Client<br/>CLI / Browser] -- "POST /chat<br/>full history" --> A\[FastAPI server]

&#x20;   A -- "validate + trim history<br/>add system prompt" --> G\[Groq LLM API]

&#x20;   G -- "reply + token usage" --> A

&#x20;   A -- "JSON or text stream" --> C

```



LLM APIs are stateless: the model does not remember earlier requests. The client keeps the conversation and sends it with every request; the server validates it, keeps the last `MAX\_HISTORY` messages and adds the system prompt before calling the model.



\## Tech stack



| Layer | Technology |

|---|---|

| API framework | FastAPI |

| Server | Uvicorn (ASGI) |

| Validation | Pydantic v2 |

| LLM provider | Groq (OpenAI-compatible API) |

| Default model | `openai/gpt-oss-20b` |

| HTTP client | httpx |



\## Getting started



\### Prerequisites



\- Python 3.10 or newer

\- A free Groq API key from \[console.groq.com](https://console.groq.com) (no credit card required)



\### Installation



```bash

git clone https://github.com/TalariAnushka/Ai\_chatbot\_API.git

cd Ai\_chatbot\_API



python -m venv venv

\# Windows

venv\\Scripts\\activate

\# macOS / Linux

source venv/bin/activate



pip install -r requirements.txt

```



\### Configuration



Copy the example settings file and add your key:



```bash

\# Windows

copy .env.example .env

\# macOS / Linux

cp .env.example .env

```



| Variable | Description | Default |

|---|---|---|

| `GROQ\_API\_KEY` | Your Groq API key (required) | none |

| `MODEL` | Groq model ID | `openai/gpt-oss-20b` |

| `MAX\_HISTORY` | Number of recent messages sent to the model | `20` |

| `SYSTEM\_PROMPT` | Instructions that set the assistant's behaviour | friendly, concise assistant |



\### Run



```bash

uvicorn main:app --reload

```



The API runs at `http://localhost:8000`, and the interactive docs are at `http://localhost:8000/docs`.



To chat from the terminal, run this in a second terminal:



```bash

python chat\_client.py            # full replies with token counts

python chat\_client.py --stream   # streaming replies

```



\## API reference



\### `GET /health`



Returns the server status and the configured model.



```json

{ "status": "ok", "model": "openai/gpt-oss-20b" }

```



\### `POST /chat`



Request:



```json

{

&#x20; "messages": \[

&#x20;   { "role": "user", "content": "What is a token?" }

&#x20; ],

&#x20; "temperature": 0.7,

&#x20; "max\_tokens": 1024

}

```



| Field | Type | Rules |

|---|---|---|

| `messages` | list | At least one message; the last must have role `user` |

| `messages\[].role` | string | `user` or `assistant` |

| `messages\[].content` | string | 1 to 20,000 characters |

| `temperature` | number | 0.0 to 2.0, default 0.7 |

| `max\_tokens` | integer | 1 to 4096, default 1024 |



Response:



```json

{

&#x20; "reply": "A token is a small chunk of text that a language model reads and writes...",

&#x20; "model": "openai/gpt-oss-20b",

&#x20; "input\_tokens": 42,

&#x20; "output\_tokens": 57,

&#x20; "messages\_sent": 1

}

```



\### `POST /chat/stream`



Same request body as `/chat`. Returns the reply as a plain-text stream.



\### Error responses



| Status | Meaning |

|---|---|

| `400` | The last message is not from the user |

| `422` | The request body failed validation |

| `429` | The provider's rate limit was reached |

| `500` | The server's API key is missing or invalid |

| `502` | The provider returned an error (for example, an unknown model) |

| `503` | The provider could not be reached |



\## Project structure



```

Ai\_chatbot\_API/

|-- main.py            # FastAPI app: endpoints, validation, LLM calls

|-- chat\_client.py     # Terminal client that keeps conversation history

|-- requirements.txt   # Pinned dependencies

|-- .env.example       # Settings template (copy to .env)

|-- .gitignore

|-- LICENSE

`-- README.md

```



\## Design decisions



\- \*\*Client-side history.\*\* Keeping the conversation on the client keeps the server stateless and easy to scale; the trade-off is that every request resends the history, which `MAX\_HISTORY` bounds.

\- \*\*Provider-agnostic configuration.\*\* The model ID lives in `.env`, so a retired or replaced model can be swapped without touching code.

\- \*\*Fail fast.\*\* Validation runs before the model call, so malformed requests never spend tokens.

\- \*\*Async I/O.\*\* Endpoints are `async`, so the server keeps handling other requests while waiting on the model.



\## Roadmap



\- \[ ] Persist conversations in a database

\- \[ ] Authentication with API keys

\- \[ ] Response caching with Redis

\- \[ ] Docker image and cloud deployment

\- \[ ] Structured logging and request metrics

\- \[ ] Automated tests



\## License



This project is licensed under the MIT License. See \[LICENSE](LICENSE) for details.

