"""
03 — 并发 vs 串行：gather / create_task
"""
import asyncio
import time


async def work(name: str, seconds: float) -> str:
    print(f"  [{time.perf_counter() - T0:5.2f}s] start {name}")
    await asyncio.sleep(seconds)
    print(f"  [{time.perf_counter() - T0:5.2f}s] done  {name}")
    return f"{name}->ok"


async def serial():
    print("\n--- 串行 (await 接 await) ---")
    a = await work("A", 1.0)
    b = await work("B", 1.0)
    return [a, b]


async def concurrent_gather():
    print("\n--- 并发 (gather) ---")
    return await asyncio.gather(work("A", 1.0), work("B", 1.0))


async def concurrent_tasks():
    print("\n--- 并发 (create_task + await) ---")
    # create_task 立刻把协程丢进事件循环开始跑
    t1 = asyncio.create_task(work("A", 1.0))
    t2 = asyncio.create_task(work("B", 1.0))
    # 这里 await 只是「等结果」，两个任务已经在并发了
    return [await t1, await t2]


async def main():
    global T0
    for fn in (serial, concurrent_gather, concurrent_tasks):
        T0 = time.perf_counter()
        results = await fn()
        elapsed = time.perf_counter() - T0
        print(f"  >> 耗时 {elapsed:.2f}s, 结果 {results}")


if __name__ == "__main__":
    asyncio.run(main())
