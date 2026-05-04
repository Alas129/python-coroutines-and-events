"""
04 — 偷看事件循环
观察任务被调度的顺序、call_soon / call_later 的语义。
"""
import asyncio


async def task(name: str, n: int):
    for i in range(n):
        print(f"  [{name}] step {i}")
        await asyncio.sleep(0)   # 让出一次（不睡，只是把控制权还给 loop）
    print(f"  [{name}] DONE")


async def demo_interleaving():
    print("--- 多任务交错（每个 await 都是切换点）---")
    await asyncio.gather(task("A", 3), task("B", 3), task("C", 3))


async def demo_call_soon_and_later():
    print("\n--- loop.call_soon / call_later（不需要协程也能调度回调）---")
    loop = asyncio.get_running_loop()
    loop.call_soon(lambda: print("  call_soon: 立刻在下一轮执行"))
    loop.call_later(0.2, lambda: print("  call_later(0.2): 200ms 后执行"))
    loop.call_later(0.1, lambda: print("  call_later(0.1): 100ms 后执行"))
    await asyncio.sleep(0.3)
    print("  主协程结束")


async def demo_blocking_kills_loop():
    """
    重要演示：在协程里写阻塞代码会卡住整个 loop。
    这里用一个故意 CPU 密集的循环。
    """
    import time
    print("\n--- 反例：在协程里阻塞 CPU 会饿死其他任务 ---")

    async def cpu_hog():
        print("  cpu_hog: 开始忙循环 1 秒（不 await）")
        end = time.perf_counter() + 1.0
        while time.perf_counter() < end:
            pass   # ❌ 整个事件循环被卡在这里
        print("  cpu_hog: 结束")

    async def heartbeat():
        for i in range(5):
            print(f"  heartbeat: tick {i}")
            await asyncio.sleep(0.2)

    # 同时启动：你会看到 heartbeat 在 cpu_hog 跑完前完全没机会
    await asyncio.gather(cpu_hog(), heartbeat())


async def main():
    await demo_interleaving()
    await demo_call_soon_and_later()
    await demo_blocking_kills_loop()


if __name__ == "__main__":
    asyncio.run(main())
