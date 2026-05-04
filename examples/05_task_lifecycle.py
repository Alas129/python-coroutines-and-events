"""
05 — Task 生命周期与异常处理
"""
import asyncio


async def succeed():
    await asyncio.sleep(0.1)
    return 42


async def fail():
    await asyncio.sleep(0.1)
    raise ValueError("something broke")


async def demo_states():
    print("--- Task 状态切换 ---")
    t = asyncio.create_task(succeed())
    print(f"  刚创建: done={t.done()}")
    await asyncio.sleep(0)             # 让 t 跑一小步
    print(f"  让出一次后: done={t.done()}")
    result = await t
    print(f"  await 后: done={t.done()}, result={result}")


async def demo_exception_caught():
    print("\n--- 在 await 处接住异常 ---")
    t = asyncio.create_task(fail())
    try:
        await t
    except ValueError as e:
        print(f"  抓到了: {e!r}")


async def demo_exception_lost():
    """
    反例：create_task 后如果没人 await 也没装回调，
    异常只会在 GC 时打印一句警告，很容易漏。
    """
    print("\n--- 反例：异常被丢失 ---")
    asyncio.create_task(fail())
    await asyncio.sleep(0.3)
    print("  (上面那个失败的任务异常去哪了？只会在解释器退出时看到一行 stderr)")


async def demo_done_callback():
    print("\n--- 用 add_done_callback 兜底 ---")
    def on_done(task: asyncio.Task):
        if task.cancelled():
            print("  callback: cancelled")
        elif task.exception() is not None:
            print(f"  callback: 失败 -> {task.exception()!r}")
        else:
            print(f"  callback: 成功 -> {task.result()}")

    t1 = asyncio.create_task(succeed())
    t1.add_done_callback(on_done)
    t2 = asyncio.create_task(fail())
    t2.add_done_callback(on_done)
    await asyncio.gather(t1, t2, return_exceptions=True)


async def demo_gather_first_failure_others_keep_running():
    print("\n--- gather 的坑：默认行为下其他任务不会被取消 ---")

    async def slow_ok(i):
        await asyncio.sleep(0.5)
        print(f"  slow_ok({i}) 还是跑完了")
        return i

    async def quick_fail():
        await asyncio.sleep(0.1)
        raise RuntimeError("boom")

    try:
        await asyncio.gather(slow_ok(1), quick_fail(), slow_ok(2))
    except RuntimeError as e:
        print(f"  gather raise 出来了: {e!r}")
        # 但 slow_ok(1) / slow_ok(2) 仍在后台跑，等会儿才打印
        await asyncio.sleep(0.6)


async def main():
    await demo_states()
    await demo_exception_caught()
    await demo_exception_lost()
    await demo_done_callback()
    await demo_gather_first_failure_others_keep_running()


if __name__ == "__main__":
    asyncio.run(main())
