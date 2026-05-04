# Python Coroutines / asyncio / Event Loop — Study Notes

> Goal: take you from "why do we need async at all?" to "I can write production-grade asyncio code." Each section maps to a runnable script in `examples/`.

> 中文版本见 [README-CN.md](README-CN.md)

---

## 0. Mental Model First

Before writing any code, get these terms straight:

| Term | What it is | Analogy |
|------|------------|---------|
| **Coroutine function** (`async def f(): ...`) | A **definition**. Calling it does **not** run it — you just get a coroutine object. | A "recipe" |
| **Coroutine object** | The thing you get back from calling a coroutine function. A state machine that needs to be **driven**. | A "half-cooked dish" waiting for the chef |
| **Task** | A handle that **registers a coroutine on the event loop** so it actually runs. | An order on the kitchen ticket rail |
| **Future** | A placeholder for "a result that will exist later." `Task` is a subclass of `Future`. | The receipt you exchange for food |
| **Event loop** | An infinite loop that picks ready coroutines, runs them a bit, and switches away when they `await` on I/O. | A solo chef juggling many orders |
| **`await`** | Hands control **back to the event loop**, resumes when the result is ready. | "This needs 20 min to simmer — I'll prep something else" |

**The single most important sentence: asyncio is single-threaded concurrency.** It overlaps work by yielding the CPU during I/O waits. It does **not** make CPU-bound code faster.

---

## 1. Why Coroutines? (vs synchronous)

Synchronous code **blocks** the whole thread on each I/O. Hitting 100 URLs serially takes ~`(slowest URL) × 100`.

The async idea: **don't sit idle while waiting on I/O — go work on something else.**

→ See [`examples/01_why_async.py`](examples/01_why_async.py): compare `time.sleep × 5` vs `asyncio.sleep × 5`.

---

## 2. Your First Coroutine: `async def` and `await`

```python
import asyncio

async def hello(name):           # 1. define a coroutine function with `async def`
    print(f"hi {name}")
    await asyncio.sleep(1)       # 2. `await` yields control
    print(f"bye {name}")
    return name.upper()          # 3. coroutines can `return`

asyncio.run(hello("world"))      # 4. asyncio.run() boots the loop and drives this coroutine
```

**Common mistakes:**

- Writing `hello("world")` on its own does **nothing** — you'll just get a coroutine object plus a `coroutine was never awaited` warning.
- `await` is only legal inside an `async def`.
- Call `asyncio.run()` **once** at the program entry — never inside a coroutine.

→ See [`examples/02_first_coroutine.py`](examples/02_first_coroutine.py)

---

## 3. Running Coroutines Concurrently: `asyncio.gather` and `Task`

`await a(); await b()` is **serial**, not concurrent. To get real concurrency, turn coroutines into Tasks — or use `gather`.

```python
# Serial: ~2s
await work(1)
await work(1)

# Concurrent: ~1s
await asyncio.gather(work(1), work(1))

# Equivalent, more explicit
t1 = asyncio.create_task(work(1))
t2 = asyncio.create_task(work(1))
await t1
await t2
```

**Rule of thumb:** "the moment you write `await` is a synchronization point." `create_task` puts the coroutine on the loop **immediately**; `await task` only waits for the result.

→ See [`examples/03_gather_vs_serial.py`](examples/03_gather_vs_serial.py)

---

## 4. What Is the Event Loop Actually Doing?

Conceptually, the event loop is just a `while True`:

```text
while there are tasks:
    1. find tasks that are "ready" (I/O completed / timer fired / freshly scheduled)
    2. run one until it `await`s (yields) or `return`s (finishes)
    3. register its wait-object (socket, timer) with the selector
    4. selector.select() blocks until at least one fd is ready → goto 1
```

Key points:

- **Cooperative scheduling** — coroutines must `await` to yield. A CPU-bound `for` loop inside a coroutine will **freeze the entire loop**.
- At any moment, only **one** coroutine is executing Python bytecode.
- The selector uses the OS primitive (`epoll` / `kqueue` / `IOCP`), so waiting on many fds is O(1).

→ See [`examples/04_event_loop_peek.py`](examples/04_event_loop_peek.py): drive the loop manually and watch scheduling order.

---

## 5. Task Lifecycle and Exception Handling

A Task is in one of: **Pending → Running → Done(result) / Cancelled / Done(exception)**.

**Most common pitfall:**

```python
async def boom():
    raise ValueError("bad")

asyncio.create_task(boom())  # ❌ no one awaits → exception swallowed, only logged on GC
```

The fix:

```python
t = asyncio.create_task(boom())
try:
    await t
except ValueError:
    ...
```

Or attach a callback:

```python
def _handle(task):
    if task.exception():
        log.error("task failed", exc_info=task.exception())
t.add_done_callback(_handle)
```

`gather`'s default behavior: **the first exception propagates out**, but the **other tasks keep running** (they are not cancelled). If you want "one fails → all cancelled," use `asyncio.TaskGroup` (Python 3.11+, strongly recommended).

→ See [`examples/05_task_lifecycle.py`](examples/05_task_lifecycle.py)
→ See [`examples/06_task_group.py`](examples/06_task_group.py)

---

## 6. Cancellation and Timeouts

```python
# Per-call timeout
try:
    result = await asyncio.wait_for(fetch(), timeout=2.0)
except asyncio.TimeoutError:
    ...

# Block-level timeout (3.11+)
async with asyncio.timeout(2.0):
    result = await fetch()
```

How cancellation works: the runtime raises `asyncio.CancelledError` at the target Task's next `await` point.

**Important:** do not use `except Exception:` to catch everything — you'll **accidentally swallow `CancelledError`**. Either let `CancelledError` pass through, or `except Exception` plus a separate `except CancelledError: raise`.

→ See [`examples/07_cancel_and_timeout.py`](examples/07_cancel_and_timeout.py)

---

## 7. Synchronization Primitives: Lock / Semaphore / Queue

Even though it's single-threaded, you still need primitives — tasks interleave at every `await`.

| Use case | API |
|----------|-----|
| Mutual exclusion (one at a time in critical section) | `asyncio.Lock` |
| Rate limiting (at most N concurrent) | `asyncio.Semaphore(N)` |
| Producer / consumer | `asyncio.Queue` |
| One-shot broadcast | `asyncio.Event` |

`Semaphore` is the workhorse — perfect for "at most 10 concurrent HTTP requests."

→ See [`examples/08_semaphore_pool.py`](examples/08_semaphore_pool.py)
→ See [`examples/09_producer_consumer.py`](examples/09_producer_consumer.py)

---

## 8. Putting Sync Code Inside asyncio: `run_in_executor` / `to_thread`

If you must call a **blocking** library (e.g. `requests`, large file reads, `time.sleep`), don't `await` it directly — push it to a thread pool:

```python
# Preferred (3.9+)
data = await asyncio.to_thread(blocking_func, arg1, arg2)

# Older form
loop = asyncio.get_running_loop()
data = await loop.run_in_executor(None, blocking_func, arg1, arg2)
```

For CPU-bound work, threads don't help (GIL) — use `ProcessPoolExecutor`.

→ See [`examples/10_blocking_to_thread.py`](examples/10_blocking_to_thread.py)

---

## 9. A Slightly Real Project: Concurrent URL Fetcher (rate-limit + retry + timeout)

Combines everything: `TaskGroup` + `Semaphore` + `timeout` + exception classification.

→ See [`examples/11_real_world_fetcher.py`](examples/11_real_world_fetcher.py)

Recommended: `pip install aiohttp` (the script falls back to `urllib + to_thread` if not installed).

---

## 10. Common Pitfall Checklist (memorize this and you avoid 80% of bugs)

1. **Forgot `await`** — calling `some_coro()` on its own does nothing and emits a warning.
2. **Calling blocking functions inside a coroutine** — `time.sleep(1)` / `requests.get(...)` freeze the entire loop. Use `await asyncio.sleep` / `aiohttp` / `asyncio.to_thread`.
3. **CPU-bound loop in `async def`** — starves every other task. Move it to `to_thread` or a process pool.
4. **Swallowing `CancelledError`** — when you use a broad `except`, remember to `raise` it.
5. **Nested `asyncio.run()`** — calling it inside an already-running loop errors out. In Jupyter, just `await` directly, or use `nest_asyncio`.
6. **Bare `create_task` without keeping a reference** — local variable can get GC'd, taking the task with it. Either `await` it or stash it in a set.
7. **Mixing threads with the loop** — every thread has its own loop. Cross-thread interaction goes through `loop.call_soon_threadsafe` / `asyncio.run_coroutine_threadsafe`.
8. **`gather`'s `return_exceptions`** — defaults to `False`: the first exception ends `gather`'s wait, but the **other tasks keep running!** Either pass `return_exceptions=True` to collect everything, or switch to `TaskGroup` (auto-cancels siblings).

---

## 11. Where to Go Next

1. Run every script in `examples/` once. Then deliberately break a few things and observe how they fail.
2. Skim PEP 492 (async/await syntax) and PEP 3156 (asyncio design). One pass each is enough.
3. Real practice: take a piece of "hit N HTTP / DB endpoints" sync code from your job and rewrite it with asyncio. Measure the speedup.
4. Useful libraries: `aiohttp` (HTTP client/server), `anyio` (async abstraction layer compatible with trio), `asyncpg` (fastest Postgres driver).
5. Going under the hood: read the `_run_once` method in CPython's `Lib/asyncio/base_events.py`. That's the event loop itself.

---

## How to Run These Examples

```bash
cd asyncio_tutorial
python3 examples/01_why_async.py
python3 examples/02_first_coroutine.py
# ...
# Example 11 needs:
pip install aiohttp
python3 examples/11_real_world_fetcher.py
```

Python 3.11+ gives the best experience (`TaskGroup` and `asyncio.timeout` were added in 3.11).
