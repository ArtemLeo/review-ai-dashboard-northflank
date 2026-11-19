"""Errors raised by the AI provider layer."""


class AiProviderError(ValueError):
    """The AI provider is misconfigured or answered with something unusable.

    It covers a missing API key and a reply that is not the expected JSON or
    chat completion shape.  Network failures stay ``httpx.HTTPError``, so the
    background task can still retry them; this error is none of the
    temporary failures the task retries, so it is treated as permanent.
    """
