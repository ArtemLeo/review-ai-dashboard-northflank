"""Doubles shared by the backend test suite.

The Redis doubles implement the exact commands the rate limiter and the session
denylist use, so their logic is exercised without a running Redis server.  The
chat server double answers like an AI provider over a real local socket.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import redis


class FakePipeline:
    """Minimal in-memory stand-in for a Redis pipeline.

    It implements the exact command sequence the limiter uses, so the
    sliding-window logic is exercised without a running Redis server.
    """

    def __init__(self, store: dict[str, dict[str, float]], owner: "FakeRedis") -> None:
        """Initialise the pipeline with the shared window store."""
        self.store = store
        self.owner = owner
        self.queued: list[tuple[str, tuple[Any, ...]]] = []

    def zremrangebyscore(self, key: str, min_score: Any, max_score: Any) -> "FakePipeline":
        """Queue a range removal."""
        self.queued.append(("zremrangebyscore", (key, min_score, max_score)))
        return self

    def zcard(self, key: str) -> "FakePipeline":
        """Queue a cardinality read."""
        self.queued.append(("zcard", (key,)))
        return self

    def zadd(self, key: str, mapping: dict[str, float]) -> "FakePipeline":
        """Queue a member insertion."""
        self.queued.append(("zadd", (key, mapping)))
        return self

    def expire(self, key: str, seconds: int) -> "FakePipeline":
        """Queue a key expiry."""
        self.queued.append(("expire", (key, seconds)))
        return self

    def execute(self) -> tuple:
        """Run the queued commands and return their results."""
        if self.owner.fail:
            raise redis.RedisError("connection refused")
        results: list = []
        for name, args in self.queued:
            if name == "zremrangebyscore":
                key, _min_score, max_score = args
                window = self.store.get(key, {})
                self.store[key] = {member: score for member, score in window.items() if score > max_score}
                results.append(len(window) - len(self.store[key]))
            elif name == "zcard":
                (key,) = args
                results.append(len(self.store.get(key, {})))
            elif name == "zadd":
                key, mapping = args
                self.store.setdefault(key, {}).update(mapping)
                results.append(len(mapping))
            else:
                results.append(True)
        self.queued.clear()
        return tuple(results)


class FakeRedis:
    """In-memory Redis double that stores the sliding windows."""

    def __init__(self) -> None:
        """Initialise the empty window store."""
        #: Sorted sets as plain dicts: key -> {member: score}.
        self.store: dict[str, dict[str, float]] = {}
        self.values: dict[str, str] = {}
        self.fail: bool = False

    def pipeline(self) -> FakePipeline:
        """Return a pipeline bound to the shared store."""
        return FakePipeline(self.store, self)

    def zrem(self, key: str, *members: str) -> int:
        """Remove members from one window.

        Args:
            key: The Redis key holding the window.
            members: The members to remove.

        Returns:
            The number of removed members.
        """
        if self.fail:
            raise redis.RedisError("connection refused")
        window = self.store.get(key, {})
        removed = [member for member in members if window.pop(member, None) is not None]
        return len(removed)

    def delete(self, key: str) -> int:
        """Drop the window of one client, giving the budget back.

        Args:
            key: The Redis key holding the window.

        Returns:
            The number of removed keys.
        """
        if self.fail:
            raise redis.RedisError("connection refused")
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Store a plain value (the expiry is irrelevant within one test)."""
        if self.fail:
            raise redis.RedisError("connection refused")
        self.values[key] = value
        return True

    def exists(self, key: str) -> int:
        """Return 1 when a plain value is stored under the key."""
        if self.fail:
            raise redis.RedisError("connection refused")
        return int(key in self.values)


#: Analysis the fake AI provider returns for every review.
FAKE_ANALYSIS: dict[str, Any] = {
    "rating": 2,
    "priority": "high",
    "category": "Bug",
    "needs_urgent_response": True,
    "language_code": "en",
}

#: Draft reply the fake AI provider returns for every review.
FAKE_DRAFT = "We are sorry about the crash, a fix is on its way."


class _ChatHandler(BaseHTTPRequestHandler):
    """Answer a chat completion request; a JSON-mode request gets the analysis."""

    # HTTP/1.1 keeps the connection alive, like the real providers do, so the
    # client pools it between requests.
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        """Read the request and answer with a chat completion body."""
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        content = json.dumps(FAKE_ANALYSIS) if "response_format" in payload else FAKE_DRAFT
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        """Keep the access log out of the test output."""


class FakeChatServer(ThreadingHTTPServer):
    """Local OpenAI-compatible chat endpoint served over a real socket.

    ``httpx.MockTransport`` never opens a connection, so it cannot show what
    happens to a pooled keep-alive connection once the event loop that opened
    it has been closed.  A test that needs the real network path points the
    provider at this server instead.
    """

    # Stopping must not wait for a keep-alive connection a client left open.
    block_on_close = False

    def __init__(self) -> None:
        """Bind to a free local port and start serving in the background."""
        super().__init__(("127.0.0.1", 0), _ChatHandler)
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def endpoint(self) -> str:
        """URL of the chat completions endpoint."""
        return f"http://127.0.0.1:{self.server_port}/v1/chat/completions"

    def stop(self) -> None:
        """Stop serving and release the port."""
        self.shutdown()
        self.server_close()
