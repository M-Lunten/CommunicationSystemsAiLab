"""Reference solutions, released into the framework after each lecture's session.

After MM5: stop-and-wait ARQ (used as the default link layer from MM6 on).
After MM6: the MACs from Lecture 6 (TDMA, slotted ALOHA, grouped ALOHA, back-off ALOHA).
"""
from .link import StopAndWaitReceiver, StopAndWaitSender
from .mac import AlwaysTransmit, BackoffAloha, GroupedAloha, RoundRobinTDMA, SlottedAloha

__all__ = ["StopAndWaitSender", "StopAndWaitReceiver", "AlwaysTransmit", "RoundRobinTDMA",
           "SlottedAloha", "GroupedAloha", "BackoffAloha"]
