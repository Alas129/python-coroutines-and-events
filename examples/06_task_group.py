"""
06 — TaskGroup（Python 3.11+ 推荐用法）
和 gather 的关键区别：
- 进入 with 块创建任务，退出时自动等所有任务结束
- 任意一个失败 → 其余任务被自动取消
- 多个异常会被打包成 ExceptionGroup
"""
import asyncio
import sys


async def work(name: str, delay: float, fail: bool = False) -> str:
    print(f"  [{name}] start (delay={delay}s, fail={fail})")
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        print(f"  [{name}] CANCELLED")
        raise
    if fail:
        raise RuntimeError(f"{name} boom")
    print(f"  [{name}] done")
    return name


async def demo_happy_path():
    print("--- 正常路径 ---")
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(work("A", 0.3))
        t2 = tg.create_task(work("B", 0.5))
        t3 = tg.create_task(work("C", 0.4))
    # 退出 with 时所有任务都已结束
    print(f"  结果: {[t.result() for t in (t1, t2, t3)]}")


async def demo_one_fails_others_cancelled():
    print("\n--- 一个失败 → 其他被取消 ---")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(work("slow-1", 2.0))
            tg.create_task(work("boom",   0.2, fail=True))
            tg.create_task(work("slow-2", 2.0))
    except* RuntimeError as eg:    # except* 解开 ExceptionGroup
        for err in eg.exceptions:
            print(f"  抓到 RuntimeError: {err}")


async def main():
    if sys.version_info < (3, 11):
        print("TaskGroup 需要 Python 3.11+，当前版本太低，跳过。")
        return
    await demo_happy_path()
    await demo_one_fails_others_cancelled()


if __name__ == "__main__":
    asyncio.run(main())
