import asyncio
import functools
import logging
import random

from google import genai
from google.genai import errors as genai_errors

from app.config import GEMINI_API_KEY

log = logging.getLogger("parcelpilot.gemini")

_client: genai.Client | None = None

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


async def call_with_retry(fn, *args, max_attempts: int = 4, base_delay: float = 1.0, **kwargs):
    """Retry-with-backoff wrapper for Gemini calls (429/5xx/timeout)."""
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await asyncio.to_thread(functools.partial(fn, *args, **kwargs))
        except genai_errors.APIError as exc:
            status = getattr(exc, "code", None)
            last_exc = exc
            if status not in RETRYABLE_STATUS or attempt == max_attempts - 1:
                raise
            delay = base_delay * (2**attempt) + random.uniform(0, 0.5)
            log.warning("Gemini call failed (status=%s), retrying in %.1fs", status, delay)
            await asyncio.sleep(delay)
        except (TimeoutError, ConnectionError) as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2**attempt) + random.uniform(0, 0.5)
            log.warning("Gemini call timed out, retrying in %.1fs", delay)
            await asyncio.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError("unreachable")
