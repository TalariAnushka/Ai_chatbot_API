"""
AI Email Generator — Week 3-4 build.

Concepts in this file:
- Structured outputs: the model MUST return JSON matching our schema
- JSON Schema generated automatically from a Pydantic model
- Validating the model's output (never trust it blindly)
- Retrying once when the output is invalid
- APIRouter: grouping related endpoints in their own file
"""

import os
from typing import Literal

import groq
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from llm_errors import to_http_error

load_dotenv()  # this module reads settings at import time, so load .env here too

MODEL = os.getenv("MODEL", "openai/gpt-oss-20b")
MAX_ATTEMPTS = 2

client = groq.AsyncGroq()
router = APIRouter(prefix="/email", tags=["Email generator"])

Tone = Literal["formal", "friendly", "persuasive", "apologetic"]
Length = Literal["short", "medium", "long"]


# ---------- What the user sends us ----------
class EmailRequest(BaseModel):
    recipient: str = Field(min_length=1, max_length=200,
                           description="Who the email is for, e.g. 'my manager Priya'")
    purpose: str = Field(min_length=5, max_length=1000,
                         description="What the email should achieve")
    key_points: list[str] = Field(default_factory=list, max_length=10,
                                  description="Facts or points the email must include")
    tone: Tone = "formal"
    length: Length = "medium"
    sender_name: str | None = Field(default=None, max_length=100)


# ---------- What the model must return (the structured output) ----------
class Email(BaseModel):
    """A complete email, split into parts."""
    model_config = ConfigDict(extra="forbid")  # no extra fields allowed

    subject: str
    greeting: str
    body: str
    closing: str
    tone: Tone


# Pydantic writes the JSON Schema for us, so the schema and our code never disagree.
EMAIL_SCHEMA = Email.model_json_schema()


# ---------- What our API returns ----------
class EmailResponse(BaseModel):
    email: Email
    model: str
    input_tokens: int
    output_tokens: int
    attempts: int  # how many tries it took to get a valid email


LENGTH_GUIDE = {
    "short": "under 80 words",
    "medium": "80 to 150 words",
    "long": "150 to 250 words",
}

SYSTEM_PROMPT = (
    "You are an expert email writer. Write clear, natural emails that achieve the "
    "sender's purpose. Include every key point the user gives. Do not invent facts, "
    "names, dates or numbers that were not provided. Put the greeting, body and "
    "closing in their own fields; the body must not repeat the greeting or closing."
)


def build_prompt(req: EmailRequest) -> str:
    points = "\n".join(f"- {p}" for p in req.key_points) or "- (none)"
    sender = req.sender_name or "leave the sender's name out of the closing"
    return (
        f"Recipient: {req.recipient}\n"
        f"Purpose: {req.purpose}\n"
        f"Key points:\n{points}\n"
        f"Tone: {req.tone}\n"
        f"Body length: {LENGTH_GUIDE[req.length]}\n"
        f"Sender name: {sender}"
    )


@router.post("/generate", response_model=EmailResponse)
async def generate_email(req: EmailRequest):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(req)},
    ]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "email", "strict": True, "schema": EMAIL_SCHEMA},
                },
            )
        except groq.BadRequestError:
            # The provider sometimes rejects output that failed schema checks: try again.
            continue
        except groq.APIError as err:
            raise to_http_error(err)

        # Never trust model output blindly: validate it against the same schema.
        try:
            email = Email.model_validate_json(response.choices[0].message.content or "")
        except ValidationError:
            continue

        return EmailResponse(
            email=email,
            model=response.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            attempts=attempt,
        )

    raise HTTPException(502, "The model did not return a valid email. Please try again.")
