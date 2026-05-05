"""
09 — 生产者 / 消费者 with asyncio.Queue
经典模式：1 个生产者塞数据，N 个消费者拉数据。
"""
import asyncio
import random


async def producer(queue: asyncio.Queue, n_items: int):
    for i in range(n_items):
        await asyncio.sleep(random.uniform(0.05, 0.15))
        item = f"item-{i}"
        await queue.put(item)
        print(f"  [P] put {item}, queue size = {queue.qsize()}")
    print("  [P] done producing")


async def consumer(queue: asyncio.Queue, name: str):
    while True:
        item = await queue.get()
        try:
            await asyncio.sleep(random.uniform(0.1, 0.3))
            print(f"  [{name}] consumed {item}")
        finally:
            queue.task_done()        # 让 queue.join() 知道这条处理完了


async def main():
    queue: asyncio.Queue = asyncio.Queue(maxsize=5)

    # 多个消费者
    consumers = [asyncio.create_task(consumer(queue, f"C{i}")) for i in range(3)]

    # 生产者
    await producer(queue, n_items=12)

    # 等所有 put 进去的都被消费完
    await queue.join()
    print("  queue 全部消费完")

    # 优雅退出消费者
    for c in consumers:
        c.cancel()
    # 等取消传播完
    await asyncio.gather(*consumers, return_exceptions=True)
    print("  消费者已退出")


if __name__ == "__main__":
    asyncio.run(main())
