"""Reference solutions, released into the framework after each lecture's session.

After MM5: stop-and-wait ARQ (used as the default link layer from MM6 on).
After MM6: the MACs from Lecture 6 (TDMA, slotted ALOHA, grouped ALOHA, back-off ALOHA).
After MM7: the packet-size helper and the retry rule.
"""
from .layers import packet_sizes, retry_decision
from .link import StopAndWaitReceiver, StopAndWaitSender
from .mac import AlwaysTransmit, BackoffAloha, GroupedAloha, RoundRobinTDMA, SlottedAloha

__all__ = ["StopAndWaitSender", "StopAndWaitReceiver", "AlwaysTransmit", "RoundRobinTDMA",
           "SlottedAloha", "GroupedAloha", "BackoffAloha", "packet_sizes", "retry_decision"]
