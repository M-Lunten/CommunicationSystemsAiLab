"""Discrete-event simulation kernel.

Everything in CommSim happens as events on one clock (seconds). You never need to
touch this file: protocols interact with time only through `ctx.now` and timers.
"""
import heapq
import itertools


class Simulator:
    def __init__(self):
        self.now = 0.0
        self._queue = []
        self._counter = itertools.count()

    def schedule(self, delay, fn, *args, priority=0):
        """Run fn(*args) after `delay` seconds. Lower priority runs first at equal times."""
        event = [self.now + delay, priority, next(self._counter), fn, args, True]
        heapq.heappush(self._queue, event)
        return event

    @staticmethod
    def cancel(event):
        if event is not None:
            event[5] = False

    def run(self, until=float("inf"), stop_when=None):
        while self._queue:
            time, _, _, fn, args, active = heapq.heappop(self._queue)
            if not active:
                continue
            if time > until:
                self.now = until
                return
            self.now = time
            fn(*args)
            if stop_when is not None and stop_when():
                return
