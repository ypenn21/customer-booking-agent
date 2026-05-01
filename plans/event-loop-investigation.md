# Event Loop Investigation: "Future Attached to a Different Loop"

## The Error

```
RuntimeError: Task <Task pending name='Task-254' coro=<TCPConnector._resolve_host_with_throttle()>> 
got Future <Future pending cb=[_chain_future.<locals>._call_check_cancel()]> 
attached to a different loop
```

This fires on the **second (and subsequent) requests** to a deployed Agent Engine instance and works on the first.

---

## Root Cause: Three Interlocking Problems

### Problem 1 — ADK spins a new thread + event loop per request

In `google/adk/runners.py:484`:
```python
def _asyncio_thread_main():
    asyncio.run(_invoke_run_async())   # new event loop every call

thread = create_thread(target=_asyncio_thread_main)
thread.start()
```

Every incoming request gets its own OS thread. Inside that thread, `asyncio.run()` is supposed to create a **brand-new** event loop, run the coroutine, then **close and discard** the loop.

---

### Problem 2 — `nest_asyncio.apply()` breaks loop lifecycle

Both `customers/agent.py` and `bookings/agent.py` call `nest_asyncio.apply()` at module load. `nest_asyncio` replaces `asyncio.run` with (`nest_asyncio.py:25`):

```python
def run(main, *, debug=False):
    loop = asyncio.get_event_loop()
    loop.set_debug(debug)
    return loop.run_until_complete(task)
    # NOTE: loop.close() is NEVER called
```

**Result**: After each request completes, the event loop for that thread is left open (not closed). Loop A from request 1 is still "alive" even though its thread has exited.

---

### Problem 3 — `Gemini.api_client` is a `@cached_property` on a shared instance

In `google/adk/models/google_llm.py:298`:
```python
@cached_property
def api_client(self) -> Client:
    return Client(http_options=...)   # created once per Gemini instance
```

And inside that `Client`, `google/genai/_api_client.py:763`:
```python
async def _get_aiohttp_session(self):
    if (
        self._aiohttp_session is None
        or self._aiohttp_session.closed
        or self._aiohttp_session._loop.is_closed()   # ← the guard
    ):
        self._aiohttp_session = AiohttpClientSession(
            connector=AiohttpTCPConnector(limit=0), ...
        )
    return self._aiohttp_session
```

The aiohttp session is recreated only when the old session's loop is closed. Because `nest_asyncio` **never closes** event loops, `_loop.is_closed()` always returns `False`, so the session is **never** recreated.

---

## The Failure Timeline

| Step | Thread | Loop | What happens |
|------|--------|------|-------------|
| Module load | main | — | `root_agent = create_agent()` runs once; `Gemini.api_client` is lazy (not yet created) |
| Request 1 | T1 | **Loop A** | `asyncio.run()` → nest_asyncio uses Loop A. First LLM call → `_get_aiohttp_session()` → session is None → creates **Session A** with `connector._loop = Loop A`. Request succeeds. |
| After req 1 | T1 | **Loop A** | nest_asyncio does NOT close Loop A. Loop A is "done" but `.is_closed()` == **False**. |
| Request 2 | T2 | **Loop B** | `asyncio.run()` → nest_asyncio creates Loop B in T2. LLM call → `_get_aiohttp_session()` → Session A exists, Loop A not closed → **returns Session A unchanged**. Session A's connector has `self._loop = Loop A`. |
| DNS resolve | T2 | **Loop B** | `TCPConnector._resolve_host()` calls `self._loop.create_task(...)` → task is in Loop A. `asyncio.shield(task)` runs in Loop B. Loop B says "this future belongs to a different loop." → **RuntimeError** |

The `Task-254` naming in the error shows many prior tasks were created (the connector accumulated tasks across requests), confirming the connector (and its loop binding) is being reused long-term.

---

## Why `api_client=None` Does Not Help

The comment in `create_agent()` says:
```python
api_client=None,  # Force fresh client creation for this instance
```

This only creates a fresh `Client` **once per `Gemini` instance** (it's a `@cached_property`). Since `root_agent = create_agent()` runs once at module load and is passed to `AdkApp(agent=root_agent)`, the same `Gemini` instance — and thus the same `Client` and the same stale aiohttp session — is reused for every request.

---

## Why the Naive "Per-Request Wrapper" Doesn't Work in Agent Engine

Before describing the fix, here's why a simple non-`AdkApp` wrapper class fails:

### How Agent Engine actually dispatches requests

When you deploy `agent_engines.create(agent=app)`, Agent Engine:
1. Calls `app.register_operations()` to discover which method names to expose as RPC endpoints
2. Serializes `app` with `cloudpickle` and stores it in GCS
3. On the remote container, deserializes the `app` object
4. For each incoming request, calls the appropriate method **by name** on the deserialized object

`AdkApp.register_operations()` returns:
```python
{
    "": ["get_session", "list_sessions", "create_session", "delete_session"],
    "async": ["async_get_session", "async_list_sessions", "async_create_session", ...],
    "stream": ["stream_query"],
    "async_stream": ["async_stream_query", "streaming_agent_run_with_events"],
}
```

A non-`AdkApp` wrapper that only has `query()`, `stream_query()`, and `register_operations()` will advertise all those method names but won't have the implementations. Agent Engine will call `create_session()` and get an `AttributeError`.

---

## The Correct Fix: Subclassing `Gemini` with a dynamic `@property`

The root cause is that `Gemini.api_client` is a `@cached_property` — it stores the `google.genai.Client` (and its aiohttp session) in the instance's `__dict__` on first access. Once cached, the same aiohttp session (bound to event loop A) is returned for all subsequent requests in loop B, C, etc.

The cleanest and most framework-aligned fix for multithreaded environments like Agent Engine is to subclass `Gemini` and override `api_client` with a plain `@property`. This creates a fresh `Client` per access instead of caching it long-term.

### Implementation

```python
from google.adk.models import Gemini

class UncachedGemini(Gemini):
    """Subclass of Gemini that prevents long-term caching of the HTTP client.
    
    This avoids 'Event loop is closed' or 'Different loop' errors in 
    multithreaded environments where a new thread/loop is created per request.
    """
    @property
    def api_client(self):
        # Clear the underlying cache keys to force recreation
        self.__dict__.pop("api_client", None)
        self.__dict__.pop("_api_backend", None)
        self.__dict__.pop("_live_api_client", None)
        
        # Defer to the base class descriptor to cleanly initialize a new client
        return super().api_client

def create_agent() -> Agent:
    return Agent(
        ...,
        model=UncachedGemini(
            model="gemini-3-flash-preview",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
    )
```

### Why this works

1. **Clean Object-Oriented Design**: It overrides the exact behavior causing the issue (`@cached_property`) directly on the model class.
2. **Framework-Idiomatic**: The ADK supports custom model subclasses. This avoids hacking the `__dict__` in a generic callback or wrapping the `AdkApp`.
3. **Resilience**: It works regardless of whether `nest_asyncio` is used, as it always binds the *new* client to the *currently active* loop on every access.

---

## Alternative: Remove `nest_asyncio` (Complementary)

The underlying cause is `nest_asyncio` preventing loop closure. Without it, `asyncio.run()` in `_asyncio_thread_main` would close each loop normally, and `_get_aiohttp_session()`'s `_loop.is_closed()` guard would work as designed.

However, removing `nest_asyncio` entirely may break other ADK internals, so the `UncachedGemini` subclass is the safest and most targeted fix.

---

## Summary of Applied Fixes

| File | Change |
|------|--------|
| `customers/agent.py` | Switched to `UncachedGemini` to handle multi-threaded requests. |
| `bookings/agent.py` | Switched to `UncachedGemini`. |
| `customers/app.py` | Standard `AdkApp(agent=create_agent())`. |
| `bookings/app.py` | Standard `AdkApp(agent=create_agent())`. |

The solution effectively isolates the networking layer from the framework's threading model without sacrificing the stateful benefits of the ADK.
