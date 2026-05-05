"""
08 — Semaphore：限制并发数
场景：要处理 20 个任务，但下游只允许同时 3 个并发。
"""
import asyncio
import time

CONCURRENCY = 3
TOTAL = 20


async def fetch(sem: asyncio.Semaphore, i: int) -> int:
    async with sem:                       # 进入临界区前 acquire，退出时 release
        print(f"  [{time.perf_counter() - T0:5.2f}s] in  job-{i:02d} (active≈{CONCURRENCY - sem._value})")
        await asyncio.sleep(0.5)
        print(f"  [{time.perf_counter() - T0:5.2f}s] out job-{i:02d}")
    return i * i


async def main():
    global T0
    T0 = time.perf_counter()
    sem = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(*(fetch(sem, i) for i in range(TOTAL)))
    print(f"\n  共 {len(results)} 个结果, 总耗时 {time.perf_counter() - T0:.2f}s")
    print(f"  理论下限: ceil({TOTAL}/{CONCURRENCY}) * 0.5s = {((TOTAL + CONCURRENCY - 1) // CONCURRENCY) * 0.5:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
