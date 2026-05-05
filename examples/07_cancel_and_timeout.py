"""
07 — 取消与超时
"""
import asyncio
import sys


async def slow_work(n: int) -> str:
    try:
        for i in range(n):
            await asyncio.sleep(0.5)
            print(f"  slow_work: step {i}")
        return "done"
    except asyncio.CancelledError:
        # 收到取消信号 → 做清理 → 一定要 raise（除非你确实想吞掉它）
        print("  slow_work: 收到 CancelledError, 清理资源中...")
        raise


async def demo_wait_for():
    print("--- asyncio.wait_for: 单个协程超时 ---")
    try:
        await asyncio.wait_for(slow_work(10), timeout=1.2)
    except asyncio.TimeoutError:
        print("  抓到了 TimeoutError")


async def demo_timeout_block():
    if sys.version_info < (3, 11):
        print("--- asyncio.timeout: 需要 3.11+，跳过 ---")
        return
    print("\n--- asyncio.timeout: 一段代码块超时 (3.11+) ---")
    try:
        async with asyncio.timeout(1.0):
            await slow_work(10)
    except TimeoutError:
        print("  抓到了 TimeoutError")


async def demo_manual_cancel():
    print("\n--- 手动 cancel ---")
    t = asyncio.create_task(slow_work(10))
    await asyncio.sleep(0.7)
    print("  主程序: 决定取消")
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        print("  主程序: 任务已取消")


async def demo_dont_eat_cancelled():
    """
    反例 + 正例：宽 except 的正确写法。
    """
    print("\n--- 不要吃掉 CancelledError ---")

    async def bad():
        try:
            await asyncio.sleep(10)
        except Exception as e:                     # ❌ Exception 包括 CancelledError? 在 3.8+ 中不再 (它是 BaseException) — 但要小心 Future-proofing
            print(f"  bad: 吃掉了 {type(e).__name__}")

    async def good():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            print("  good: 让 CancelledError 传播")
            raise
        except Exception as e:
            print(f"  good: 处理普通异常 {e!r}")

    for fn, label in ((bad, "bad"), (good, "good")):
        t = asyncio.create_task(fn())
        await asyncio.sleep(0.1)
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            print(f"  {label}: 主程序观察到取消传播")


async def main():
    await demo_wait_for()
    await demo_timeout_block()
    await demo_manual_cancel()
    await demo_dont_eat_cancelled()


if __name__ == "__main__":
    asyncio.run(main())
