import asyncio
import threading
from datetime import datetime, timezone

import pytest

from qibao_api.main import _hotspot_live_refresh_loop


@pytest.mark.asyncio
async def test_database_calendar_wait_does_not_block_the_api_event_loop():
    entered = threading.Event()
    release = threading.Event()
    exited = threading.Event()
    calendar_threads = []

    class Calendar:
        def is_trading_day(self, _date):
            calendar_threads.append(threading.get_ident())
            entered.set()
            try:
                release.wait(2)
                return False
            finally:
                exited.set()

    task = asyncio.create_task(_hotspot_live_refresh_loop(
        object(), Calendar(), initial_delay_seconds=0,
        clock=lambda: datetime(2026, 11, 19, 6, tzinfo=timezone.utc),
    ))
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        # This coroutine represents a progress/health request served while the
        # calendar is still waiting on the database writer in another thread.
        assert not exited.is_set()
        assert len(calendar_threads) == 1
        assert calendar_threads[0] != threading.get_ident()
    finally:
        release.set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
