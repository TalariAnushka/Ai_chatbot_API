"""
AI Chatbot API — Week 3-4 build (free version using Groq).

Concepts in this file:
- FastAPI endpoints (GET /health, POST /chat, POST /chat/stream)
- Pydantic validation (bad input -> automatic 422 error)
- Stateless LLM calls (the client sends the full history every time)
- Context management (we keep only the most recent messages)
- async/await (server stays free while waiting for the LLM)
- Streaming (tokens sent as they are generated)
- Temperature (randomness of the model's word choices)
- Meaningful HTTP status codes for errors

Run:  uvicorn main:app --reload
Docs: http://localhost:8000/docs
"""

import os
from typing import Literal

import groq
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from email_generator import router as email_router
from llm_errors import to_http_error

load_dotenv()  # reads GROQ_API_KEY etc. from a .env file

# ---------- Settings ----------
MODEL = os.getenv("MODEL", "openai/gpt-oss-20b")     # free, fast model on Groq
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))     # how many past messages we send
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a friendly, concise assistant. If you don't know something, say so.",
)

# One shared async client. It reads GROQ_API_KEY from the environment.
client = groq.AsyncGroq()

app = FastAPI(title="AI Chatbot API", version="1.2")
app.include_router(email_router)  # adds POST /email/generate


# ---------- Request / response shapes (Pydantic) ----------
class Message(BaseModel):
    role: Literal["user", "assistant"]          # only these two roles allowed
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class ChatResponse(BaseModel):
    reply: str
    model: str
    input_tokens: int        # tokens you sent
    output_tokens: int       # tokens the model generated
    messages_sent: int       # how many history messages actually went to the model


# ---------- Helpers ----------
def prepare_history(messages: list[Message]) -> list[dict]:
    """Validate the conversation, trim it, and add the system prompt."""
    if messages[-1].role != "user":
        # 400 = the client sent something logically wrong
        raise HTTPException(400, "The last message must come from the user.")

    # Truncation strategy: keep only the most recent messages.
    recent = messages[-MAX_HISTORY:]

    # The conversation sent to the model must start with a user message.
    while recent and recent[0].role != "user":
        recent = recent[1:]

    # In the OpenAI-style format Groq uses, the system prompt is the first message.
    return [{"role": "system", "content": SYSTEM_PROMPT}] + [m.model_dump() for m in recent]


# ---------- Endpoints ----------
@app.get("/health")
async def health():
    """Quick check that the server is running (used by deployments in weeks 9-10)."""
    return {"status": "ok", "model": MODEL}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = prepare_history(req.messages)
    try:
        # 'await' = wait for the LLM without blocking other users
        response = await client.chat.completions.create(
            model=MODEL,
            messages=history,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except groq.APIError as err:
        raise to_http_error(err)

    return ChatResponse(
        reply=response.choices[0].message.content or "",
        model=response.model,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        messages_sent=len(history) - 1,   # not counting the system prompt
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Same as /chat, but sends the reply piece by piece as it is generated."""
    history = prepare_history(req.messages)

    async def generate():
        try:
            stream = await client.chat.completions.create(
                model=MODEL,
                messages=history,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                text = chunk.choices[0].delta.content if chunk.choices else None
                if text:
                    yield text
        except groq.APIError as err:
            # Headers are already sent, so we report the error inside the stream.
            yield f"\n[error: {to_http_error(err).detail}]"

    return StreamingResponse(generate(), media_type="text/plain")
