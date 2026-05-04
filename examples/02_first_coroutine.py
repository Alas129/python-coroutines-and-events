"""
02 — 第一个协程
观察「协程对象」和「跑起来」的区别。
"""
import asyncio


async def hello(name: str) -> str:
    print(f"  hi {name}")
    await asyncio.sleep(0.5)
    print(f"  bye {name}")
    return name.upper()


def demo_coroutine_object_is_not_run():
    print("[1] 直接调用 async def 不会执行：")
    coro = hello("world")          # 仅仅得到一个 coroutine 对象
    print(f"    type = {type(coro).__name__}")
    print(f"    repr = {coro!r}")
    coro.close()                   # 显式关闭，避免 'never awaited' 警告
    print("    (注意：上面的 'hi world' 没有打印！)\n")


async def demo_run_with_await():
    print("[2] 用 await 真正驱动它：")
    result = await hello("alice")
    print(f"    返回值 = {result!r}\n")


async def demo_multiple_awaits_are_serial():
    print("[3] 连续 await 是串行的（注意先后顺序）：")
    await hello("A")
    await hello("B")


async def main():
    demo_coroutine_object_is_not_run()
    await demo_run_with_await()
    await demo_multiple_awaits_are_serial()


if __name__ == "__main__":
    asyncio.run(main())
