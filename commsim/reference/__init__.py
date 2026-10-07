"""Reference solutions, released into the framework after each lecture's session.

After MM5: stop-and-wait ARQ (used as the default link layer from MM6 on).
"""
from .link import StopAndWaitReceiver, StopAndWaitSender

__all__ = ["StopAndWaitSender", "StopAndWaitReceiver"]
