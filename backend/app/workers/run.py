"""Standalone scheduler worker entrypoint.

Run as a separate process/service in production so the follow-up + publishing
schedulers execute exactly once (not once per web worker):

    python -m app.workers.run
"""
import asyncio
import logging
import signal

from app.workers.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("travelos.worker")


async def main() -> None:
    start_scheduler()
    logger.info("Scheduler worker running. Press Ctrl+C to stop.")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # e.g. on Windows
            pass
    try:
        await stop.wait()
    finally:
        stop_scheduler()
        logger.info("Scheduler worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
