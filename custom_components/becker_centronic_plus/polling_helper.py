import asyncio
import logging
import time
from typing import Callable, Optional, Awaitable

_LOGGER = logging.getLogger(__name__)

class BackoffPollingTask:
    """Helper to manage a background polling task with exponential backoff."""

    def __init__(
        self,
        hass,
        logger: logging.Logger,
        task_name: str,
        initial_interval: float = 3.5,
        max_interval: float = 30.0,
        backoff_start_delay: float = 60.0,
        max_elapsed_time: Optional[float] = None,
        grace_period: float = 0.0,
    ):
        self._hass = hass
        self._logger = logger
        self._task_name = task_name
        self._initial_interval = initial_interval
        self._max_interval = max_interval
        self._backoff_start_delay = backoff_start_delay
        self._max_elapsed_time = max_elapsed_time
        self._grace_period = grace_period

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    @property
    def is_running(self) -> bool:
        """Return True if the polling task is currently active."""
        return self._task is not None and not self._task.done()

    def start(
        self,
        action: Callable[[], Awaitable[None]],
        stop_condition: Callable[[], bool],
    ) -> None:
        """Start the background polling task."""
        if self.is_running:
            return

        self._stop_event.clear()
        self._task = self._hass.async_create_background_task(
            self._run_loop(action, stop_condition),
            self._task_name,
        )

    def stop(self) -> None:
        """Stop the background polling task."""
        if self._task:
            self._task.cancel()
            self._task = None
        self._stop_event.set()

    async def wait(self) -> None:
        """Wait for the task to complete naturally."""
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self, action, stop_condition) -> None:
        """The main polling loop."""
        start_time = time.monotonic()
        current_interval = self._initial_interval

        try:
            while True:
                now = time.monotonic()
                elapsed = now - start_time

                # Check constraints
                if self._max_elapsed_time and elapsed > self._max_elapsed_time:
                    break
                if elapsed > self._grace_period and stop_condition():
                    break

                try:
                    await action()
                except Exception as err:
                    self._logger.debug("Polling action failed for %s: %s", self._task_name, err)

                # Calculate wait
                if elapsed < self._backoff_start_delay:
                    wait_time = self._initial_interval
                else:
                    current_interval = min(self._max_interval, current_interval * 2)
                    wait_time = current_interval

                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=wait_time)
                    break # Event was set, stop the loop
                except asyncio.TimeoutError:
                    pass # Continue loop after normal interval

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.exception("Error in polling task %s: %s", self._task_name, e)
        finally:
            self._task = None
            self._stop_event.set()