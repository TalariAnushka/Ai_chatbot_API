"""Shared helper: turn LLM-provider errors into clear HTTP errors for our clients."""

import groq
from fastapi import HTTPException


def to_http_error(err: Exception) -> HTTPException:
    if isinstance(err, groq.AuthenticationError):
        return HTTPException(500, "Server API key is missing or invalid.")
    if isinstance(err, groq.RateLimitError):
        return HTTPException(429, "Free-tier rate limit reached. Wait a moment and try again.")
    if isinstance(err, groq.APIConnectionError):
        return HTTPException(503, "Could not reach the AI provider.")
    if isinstance(err, groq.APIStatusError):
        return HTTPException(502, f"AI provider error: {err.message}")
    return HTTPException(500, "Unexpected server error.")
