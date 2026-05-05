# Python 协程 / asyncio / 事件循环 复习笔记

> 目标：从「为什么需要异步」到「能写出生产可用的 asyncio 代码」。每一节都对应 `examples/` 目录下一个可运行的脚本。

---

## 0. 心智模型先行

在写任何代码之前，请先把这几个名词关系搞清楚：

| 名词 | 是什么 | 类比 |
|------|--------|------|
| **协程函数** (`async def f(): ...`) | 一个**定义**，调用它**不会执行**，只会返回一个协程对象 | 像「菜谱」 |
| **协程对象** (coroutine) | 调用协程函数得到的对象，是一个可被「驱动」的状态机 | 像「按菜谱做的半成品」，需要厨师驱动 |
| **Task** | 把协程**注册到事件循环**让它后台跑起来的句柄 | 像把订单交给服务员排到队列里 |
| **Future** | 一个「未来某时刻会有结果」的占位符，Task 是 Future 的子类 | 像取餐小票 |
| **事件循环** (event loop) | 一个无限循环，不断挑出「就绪」的协程让它跑一小段、遇到 IO 等待就切走 | 像独自一人的厨师，多个订单交错处理 |
| **`await`** | 把控制权**交还**给事件循环，等结果回来再恢复 | 像厨师说「这锅得炖 20 分钟，我先去切别的菜」 |

**最关键的一句话：asyncio 是「单线程并发」**——它通过在 IO 等待时让出 CPU，让一个线程同时推进多个任务。它**不会让 CPU 密集型代码变快**。

---

## 1. 为什么需要协程？(对比同步版本)

同步代码遇到网络 / 磁盘 IO 时，整个线程**阻塞**。如果你要请求 100 个 URL，加起来的时间约等于「最慢那一个」× 100。

协程的核心想法：**等待 IO 时不要傻等，让出 CPU 去做别的事**。

→ 看 [`examples/01_why_async.py`](examples/01_why_async.py)：对比 `time.sleep` × 5 和 `asyncio.sleep` × 5 的耗时。

---

## 2. 第一个协程：`async def` 和 `await`

```python
import asyncio

async def hello(name):           # 1. 用 async def 定义协程函数
    print(f"hi {name}")
    await asyncio.sleep(1)       # 2. await 让出控制权
    print(f"bye {name}")
    return name.upper()          # 3. 协程也能 return

asyncio.run(hello("world"))      # 4. asyncio.run() 启动事件循环并跑这个协程
```

**易错点**：

- `hello("world")` 单独写一行，**什么都不会发生**，只会得到一个 coroutine 对象 + 警告 `coroutine was never awaited`。
- `await` 只能写在 `async def` 内部。
- `asyncio.run()` 只在程序入口调用一次，不要在协程内部调用。

→ 看 [`examples/02_first_coroutine.py`](examples/02_first_coroutine.py)

---

## 3. 并发跑多个协程：`asyncio.gather` 与 `Task`

直接 `await a(); await b()` 是**串行**的，不是并发。要并发必须把协程**变成 Task**，或者用 `gather`。

```python
# 串行：耗时 = 1 + 1 = 2 秒
await work(1)
await work(1)

# 并发：耗时 ≈ 1 秒
await asyncio.gather(work(1), work(1))

# 等价的、更显式的写法
t1 = asyncio.create_task(work(1))
t2 = asyncio.create_task(work(1))
await t1
await t2
```

**记忆法则**：「写下 `await` 的那一刻就是同步点」。`create_task` 把协程**立刻**丢进事件循环开始跑，`await task` 只是等它的结果。

→ 看 [`examples/03_gather_vs_serial.py`](examples/03_gather_vs_serial.py)

---

## 4. 事件循环到底在做什么？

事件循环在概念上就是一个 `while True`：

```text
while 还有任务:
    1. 看哪些任务「就绪」（IO 完成 / 定时器到点 / 刚被创建）
    2. 挑一个跑，直到它 await（让出）或 return（结束）
    3. 把它的「等待对象」(socket、定时器) 注册到 selector
    4. 用 selector.select() 等待至少一个 IO 就绪 → 回到 1
```

关键点：

- **协作式调度**——协程必须主动 `await` 才会让出。一个 CPU 密集的 `for` 循环在协程里**会卡住整个事件循环**。
- 同一时刻**只有一个**协程在 Python 字节码层面运行。
- `selector` 用的是操作系统的 `epoll` / `kqueue` / `IOCP`，等多个 fd 是 O(1) 的。

→ 看 [`examples/04_event_loop_peek.py`](examples/04_event_loop_peek.py)：手动操作 loop，观察任务调度顺序。

---

## 5. Task 的生命周期与异常处理

Task 有四种状态：**Pending → Running → Done(结果) / Cancelled / Done(异常)**。

**最容易踩的坑**：

```python
async def boom():
    raise ValueError("bad")

asyncio.create_task(boom())  # ❌ 没人 await，异常被吞，只在 GC 时打印警告
```

正确做法：

```python
t = asyncio.create_task(boom())
try:
    await t
except ValueError:
    ...
```

或者给 Task 装一个回调：

```python
def _handle(task):
    if task.exception():
        log.error("task failed", exc_info=task.exception())
t.add_done_callback(_handle)
```

`gather` 默认行为：**任一子任务异常会被传出来**，但其他任务**不会自动取消**（仍在后台跑）。如果想要「一个失败全部取消」用 `asyncio.TaskGroup`（Python 3.11+，强烈推荐）。

→ 看 [`examples/05_task_lifecycle.py`](examples/05_task_lifecycle.py)
→ 看 [`examples/06_task_group.py`](examples/06_task_group.py)

---

## 6. 取消与超时

```python
# 单个任务超时
try:
    result = await asyncio.wait_for(fetch(), timeout=2.0)
except asyncio.TimeoutError:
    ...

# 一段代码块的超时（3.11+）
async with asyncio.timeout(2.0):
    result = await fetch()
```

取消的原理：在目标 Task 的下一个 `await` 点抛出 `asyncio.CancelledError`。

**重要**：你的协程里不应该 `except Exception:` 捕获一切——会**意外吃掉 CancelledError**。要么放过 `CancelledError`，要么 `except Exception` + 单独 `except CancelledError: raise`。

→ 看 [`examples/07_cancel_and_timeout.py`](examples/07_cancel_and_timeout.py)

---

## 7. 同步原语：Lock / Semaphore / Queue

虽然是单线程，仍然需要同步原语，因为任务在 `await` 处会交错执行。

| 用途 | API |
|------|-----|
| 互斥（同时只让一个进临界区） | `asyncio.Lock` |
| 限流（最多 N 个并发） | `asyncio.Semaphore(N)` |
| 生产者/消费者 | `asyncio.Queue` |
| 一次性广播 | `asyncio.Event` |

`Semaphore` 是最常用的，做「最多并发 10 个 HTTP 请求」非常合适。

→ 看 [`examples/08_semaphore_pool.py`](examples/08_semaphore_pool.py)
→ 看 [`examples/09_producer_consumer.py`](examples/09_producer_consumer.py)

---

## 8. 把同步代码塞进 asyncio：`run_in_executor` / `to_thread`

如果你必须调用一个**阻塞**的库（例如 `requests`、读大文件、`time.sleep`），不能直接 `await`，要扔到线程池：

```python
# 推荐写法 (3.9+)
data = await asyncio.to_thread(blocking_func, arg1, arg2)

# 老写法
loop = asyncio.get_running_loop()
data = await loop.run_in_executor(None, blocking_func, arg1, arg2)
```

CPU 密集型任务用 `ProcessPoolExecutor` 才有意义，因为线程过不了 GIL。

→ 看 [`examples/10_blocking_to_thread.py`](examples/10_blocking_to_thread.py)

---

## 9. 一个真实些的小项目：异步并发抓 URL（带限流 + 重试 + 超时）

集成前面所有内容：`TaskGroup` + `Semaphore` + `timeout` + 异常处理。

→ 看 [`examples/11_real_world_fetcher.py`](examples/11_real_world_fetcher.py)

需要：`pip install aiohttp`

---

## 10. 常见陷阱清单（背下来能避 80% 的坑）

1. **忘了 `await`**：`some_coro()` 单独一行 → 什么都没发生 + 警告。
2. **在协程里调用阻塞函数**：`time.sleep(1)` / `requests.get(...)` 会卡住整个 loop。换 `await asyncio.sleep` / `aiohttp` / `asyncio.to_thread`。
3. **在 `async def` 里写 CPU 密集循环**：会饿死其他任务。改用 `to_thread` 或进程池。
4. **吃掉 `CancelledError`**：用宽 `except` 时记得 `raise` 它。
5. **`asyncio.run()` 嵌套调用**：在已经运行的 loop 里再调 `asyncio.run` 会报错。Jupyter 里要么用 `await` 直接 await，要么 `nest_asyncio`。
6. **裸 `create_task` 不存引用**：本地变量被 GC 了 task 也可能被取消。要么 `await` 它，要么放进集合里持有引用。
7. **混用线程的 loop**：每个线程有自己的 loop。跨线程交互用 `loop.call_soon_threadsafe` / `asyncio.run_coroutine_threadsafe`。
8. **`gather` 的 `return_exceptions`**：默认 `False`，第一个异常会让 `gather` 结束（其他任务继续跑！）。要么 `return_exceptions=True` 收集所有结果，要么改用 `TaskGroup`（自动 cancel 其他）。

---

## 11. 学习路线（学完这份笔记之后）

1. 把 `examples/` 全跑一遍，故意改坏几个地方观察会怎么挂。
2. 读 PEP 492（async/await 语法）和 PEP 3156（asyncio 设计）—— 看一遍就够。
3. 实战：把你工作中一段「调 N 个 HTTP / DB」的同步代码改成 asyncio，量化加速比。
4. 进阶库：`aiohttp`（HTTP 客户端/服务器）、`anyio`（异步抽象层，兼容 trio）、`asyncpg`（最快的 Postgres 驱动）。
5. 想了解底层：读 CPython 的 `Lib/asyncio/base_events.py` 里 `_run_once` 方法——那就是事件循环的本体。

---

## 怎么跑这些例子

```bash
cd asyncio_tutorial
python3 examples/01_why_async.py
python3 examples/02_first_coroutine.py
# ...
# 第 11 个需要：
pip install aiohttp
python3 examples/11_real_world_fetcher.py
```

Python 3.11+ 体验最好（`TaskGroup`、`asyncio.timeout` 都是 3.11 引入的）。
