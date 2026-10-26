# Agent Engine: Threading and Import Resolution Summary

This document summarizes the technical issues encountered during the setup of the Customer and Booking agents and the corresponding solutions implemented.

## 1. Threading & Event Loop Conflicts (`RuntimeError`)

### The Issue
When deploying agents to Vertex AI Agent Engine, we encountered the following error during cross-agent delegation:
`RuntimeError: Task <Task ...> got Future <Future ...> attached to a different loop`

**Root Causes:**
*   **Asynchronous Tool Definitions**: Defining tools as `async def` in a multi-threaded environment (like Agent Engine's runner) can lead to race conditions where `aiohttp` (used by the Vertex AI SDK) attempts to attach itself to an event loop that is either closed or belongs to a different thread.
*   **Stateful Client Reuse**: Reusing the same `Agent` or `Gemini` model instance across multiple requests causes the underlying networking clients to attempt to reuse event loops from previous requests, which are no longer valid.

### The Solution
*   **Synchronous Tools**: Changed the `bookings` delegation tool to a synchronous `def`. This ensures the SDK calls run in their own dedicated thread without trying to manage complex event loop inheritance.
*   **Model Client Reset via Subclassing**: Implemented an `UncachedGemini` subclass that overrides the `api_client` with a plain `@property`. This property invalidates the cache entries in `__dict__` before deferring to the base class, forcing the recreation of the `google-genai` client and its underlying `aiohttp` session for every access. This ensures the HTTP session always binds to the *current* thread's event loop, preventing both "different loop" and "event loop is closed" errors.
*   **Agent Factory Pattern**: Used a `create_agent()` factory function to cleanly initialize the agent with the `UncachedGemini` model.

---

## 2. Module Shadowing (`ModuleNotFoundError`)

### The Issue
The deployment script failed with:
`ModuleNotFoundError: No module named 'bookings.app'`

**Root Cause:**
*   **Namespace Collision in `__init__.py`**: The `bookings/__init__.py` file contained `from .agent import app`. 
*   In Python, if a package has an attribute (the `app` variable) with the **exact same name** as a submodule (the `app.py` file), the attribute "shadows" the module. 
*   When the script tried to run `from bookings.app import app`, Python saw the `app` object in the `bookings` namespace and stopped looking for the `app.py` file.

### The Solution
*   **Empty `__init__.py`**: Removed the exports from `__init__.py`. This cleared the namespace collision and allowed Python to correctly identify `bookings.app` as the module file `app.py`.
*   **Robust Path Insertion**: Updated deployment scripts to use `sys.path.insert(0, ...)` instead of `sys.path.append(...)`. This ensures the local project root is prioritized over any globally installed packages with similar names.

---

## Best Practices for Agent Engine Deployment
1.  **Always use a factory pattern** (`create_agent()`) to instantiate agents.
2.  **Subclass `Gemini`** and override `api_client` with a dynamic `@property` to prevent long-term caching of the HTTP client. This is the most reliable way to handle Agent Engine's multi-threaded request model.
3.  **Keep `__init__.py` empty** or use distinct names for variables and files (e.g., don't name a variable `app` inside a package that has an `app.py`).
4.  **Prefer synchronous tool definitions** for networking/delegation tasks unless specific concurrency is required within the tool itself.



## Error MSG:

{
insertId: "69f114780002f60b1d149d29"
logName: "projects/agent-security-patterns/logs/aiplatform.googleapis.com%2Freasoning_engine_stderr"
receiveTimestamp: "2026-04-28T20:11:36.508569812Z"
resource: {2}
severity: "ERROR"
textPayload: "Traceback (most recent call last):
  File "/usr/local/lib/python3.12/threading.py", line 1075, in _bootstrap_inner
    self.run()
  File "/usr/local/lib/python3.12/threading.py", line 1012, in run
    self._target(*self._args, **self._kwargs)
  File "/code/.venv/lib/python3.12/site-packages/google/adk/runners.py", line 486, in _asyncio_thread_main
    asyncio.run(_invoke_run_async())
  File "/code/.venv/lib/python3.12/site-packages/nest_asyncio.py", line 30, in run
    return loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/nest_asyncio.py", line 98, in run_until_complete
    return f.result()
           ^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/futures.py", line 202, in result
    raise self._exception.with_traceback(self._exception_tb)
  File "/usr/local/lib/python3.12/asyncio/tasks.py", line 316, in __step_run_and_handle_result
    result = coro.throw(exc)
             ^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/adk/runners.py", line 479, in _invoke_run_async
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/runners.py", line 632, in run_async
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/runners.py", line 617, in _run_with_trace
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/runners.py", line 881, in _exec_with_plugin
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/runners.py", line 606, in execute
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/agents/base_agent.py", line 297, in run_async
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/agents/llm_agent.py", line 487, in _run_async_impl
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/base_llm_flow.py", line 804, in run_async
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/base_llm_flow.py", line 881, in _run_one_step_async
    async for llm_response in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/base_llm_flow.py", line 1261, in _call_llm_async
    async for event in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/base_llm_flow.py", line 1239, in _call_llm_with_tracing
    async for llm_response in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/base_llm_flow.py", line 1322, in _run_and_handle_error
    async for response in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/base_llm_flow.py", line 406, in _run_and_handle_error
    raise model_error
  File "/code/.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/base_llm_flow.py", line 379, in _run_and_handle_error
    async for llm_response in agen:
  File "/code/.venv/lib/python3.12/site-packages/google/adk/models/google_llm.py", line 245, in generate_content_async
    response = await self.api_client.aio.models.generate_content(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/opentelemetry/instrumentation/google_genai/generate_content.py", line 1180, in instrumented_generate_content
    response = await wrapped_func(
               ^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/genai/models.py", line 8337, in generate_content
    return await self._generate_content(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/genai/models.py", line 6897, in _generate_content
    response = await self._api_client.async_request(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/genai/_api_client.py", line 1583, in async_request
    result = await self._async_request(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/genai/_api_client.py", line 1516, in _async_request
    return await self._async_retry(  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 112, in __call__
    do = await self.iter(retry_state=retry_state)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/tenacity/__init__.py", line 393, in <lambda>
    self._add_action_func(lambda rs: rs.outcome.result())
                                     ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 449, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 401, in __get_result
    raise self._exception
  File "/code/.venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 116, in __call__
    result = await fn(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/genai/_api_client.py", line 1440, in _async_request_once
    response = await self._aiohttp_session.request(  # type: ignore[union-attr]
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/auth/aio/transport/sessions.py", line 293, in request
    response = await with_timeout(
               ^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/auth/aio/transport/sessions.py", line 78, in with_timeout
    response = await asyncio.wait_for(coro, remaining)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/tasks.py", line 520, in wait_for
    return await fut
           ^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/google/auth/aio/transport/aiohttp.py", line 174, in __call__
    response = await self._session.request(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/client.py", line 788, in _request
    resp = await handler(req)
           ^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/client.py", line 742, in _connect_and_send_request
    conn = await self._connector.connect(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/connector.py", line 672, in connect
    proto = await self._create_connection(req, traces, timeout)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/connector.py", line 1251, in _create_connection
    _, proto = await self._create_direct_connection(req, traces, timeout)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/connector.py", line 1574, in _create_direct_connection
    hosts = await self._resolve_host(host, port, traces=traces)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/connector.py", line 1190, in _resolve_host
    return await asyncio.shield(resolved_host_task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/futures.py", line 289, in __await__
    yield self  # This tells Task to wait for completion.
    ^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/tasks.py", line 385, in __wakeup
    future.result()
  File "/usr/local/lib/python3.12/asyncio/futures.py", line 202, in result
    raise self._exception.with_traceback(self._exception_tb)
  File "/usr/local/lib/python3.12/asyncio/tasks.py", line 316, in __step_run_and_handle_result
    result = coro.throw(exc)
             ^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/connector.py", line 1221, in _resolve_host_with_throttle
    addrs = await self._resolver.resolve(host, port, family=self._family)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/.venv/lib/python3.12/site-packages/aiohttp/resolver.py", line 40, in resolve
    infos = await self._loop.getaddrinfo(
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/base_events.py", line 905, in getaddrinfo
    return await self.run_in_executor(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/futures.py", line 289, in __await__
    yield self  # This tells Task to wait for completion.
    ^^^^^^^^^^
RuntimeError: Task <Task pending name='Task-254' coro=<TCPConnector._resolve_host_with_throttle() running at /code/.venv/lib/python3.12/site-packages/aiohttp/connector.py:1221>> got Future <Future pending cb=[_chain_future.<locals>._call_check_cancel() at /usr/local/lib/python3.12/asyncio/futures.py:389]> attached to a different loop"
timestamp: "2026-04-28T20:11:36.194059Z"
}
