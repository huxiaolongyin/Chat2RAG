import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=5)


# TODO: Need to optimize the performance of the following code
# Key modification: Run the event loop using an independent thread
def run_async_in_thread(coro):
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
