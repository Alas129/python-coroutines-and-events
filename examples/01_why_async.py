"""
01 — 为什么需要异步？
对比同步阻塞 vs 异步并发的总耗时。
"""
import asyncio
import time


def blocking_io(name: str, seconds: float) -> str:
    print(f"[sync ] start {name}")
    time.sleep(seconds)
    print(f"[sync ] done  {name}")
    return name


async def async_io(name: str, seconds: float) -> str:
    print(f"[async] start {name}")
    await asyncio.sleep(seconds)
    print(f"[async] done  {name}")
    return name


def run_sync():
    t0 = time.perf_counter()
    for i in range(5):
        blocking_io(f"job-{i}", 1.0)
    return time.perf_counter() - t0


async def run_async():
    t0 = time.perf_counter()
    await asyncio.gather(*(async_io(f"job-{i}", 1.0) for i in range(5)))
    return time.perf_counter() - t0


if __name__ == "__main__":
    print("=== 同步版本 ===")
    sync_time = run_sync()
    print(f"\n=== 异步版本 ===")
    async_time = asyncio.run(run_async())

    print(f"\n同步总耗时: {sync_time:.2f}s   (5 个任务每个 1s, 串行)")
    print(f"异步总耗时: {async_time:.2f}s   (5 个任务每个 1s, 并发)")
    print(f"加速比: {sync_time / async_time:.1f}x")
