"""Applications: traffic sources at senders and data sinks at receivers.

The sink knows what the source really sent, so it can count exactly how much data
arrived correctly, how much arrived twice (duplicates), how much arrived corrupted
without anyone noticing (undetected errors), and how long it took.
"""
from collections import deque


class Source:
    """Base class. Subclasses decide when new payloads appear."""

    def __init__(self, payload_bytes=None):
        self.payload_bytes = payload_bytes
        self.payloads = []
        self.created = []
        self._waiting = deque()
        self.node = None
        self.peer = None
        self.net = None

    def attach(self, net, node, peer, payload_bytes):
        self.net, self.node, self.peer = net, node, peer
        if self.payload_bytes is None:
            self.payload_bytes = payload_bytes

    def _new_payload(self):
        payload = self.net.rng.bytes(self.payload_bytes)
        self.payloads.append(payload)
        self.created.append(self.net.sim.now)
        self._waiting.append(len(self.payloads) - 1)

    def _arrival(self, count=1):
        for _ in range(count):
            self._new_payload()
        ctx = self.node.context(self.peer)
        ctx.protocol.on_data_ready(ctx)

    def start(self):
        pass

    def next_payload(self):
        if not self._waiting:
            return None
        return self.payloads[self._waiting.popleft()]

    @property
    def finite_total(self):
        return None


class FileTransfer(Source):
    """All `n_packets` payloads are ready at time 0 (Alice's file in Problem Set 1)."""

    def __init__(self, n_packets, payload_bytes=None):
        super().__init__(payload_bytes)
        self.n_packets = n_packets

    def start(self):
        for _ in range(self.n_packets):
            self._new_payload()

    @property
    def finite_total(self):
        return self.n_packets


class Saturated(Source):
    """There is always a new payload waiting."""

    def next_payload(self):
        self._new_payload()
        return super().next_payload()


class Bernoulli(Source):
    """In every slot a new payload arrives with probability `rate` (packets per slot)."""

    def __init__(self, rate, payload_bytes=None):
        super().__init__(payload_bytes)
        self.rate = rate

    def start(self):
        self._schedule_next()

    def _schedule_next(self):
        if self.rate <= 0:
            return
        self._slot = getattr(self, "_slot", 0) + int(self.net.rng.geometric(self.rate))
        self.net.at_slot(self._slot, self._tick)

    def _tick(self):
        self._arrival()
        self._schedule_next()


class Bursty(Source):
    """Mostly silent; with probability `prob` per slot a burst of `size` payloads arrives
    (the smart doorbell of the pre-lecture reading)."""

    def __init__(self, prob, size, payload_bytes=None):
        super().__init__(payload_bytes)
        self.prob, self.size = prob, size

    def start(self):
        self._schedule_next()

    def _schedule_next(self):
        self._slot = getattr(self, "_slot", 0) + int(self.net.rng.geometric(self.prob))
        self.net.at_slot(self._slot, self._tick)

    def _tick(self):
        self._arrival(self.size)
        self._schedule_next()


class Sink:
    """Receives payloads for one sender and compares them with what was really sent."""

    LOOKAHEAD = 64

    def __init__(self, source, net):
        self.source = source
        self.net = net
        self.next = 0
        self.correct = 0
        self.duplicates = 0
        self.wrong = 0
        self.missing = 0
        self.delays = []
        self.last_delivery = 0.0

    def deliver(self, payload):
        sent = self.source.payloads
        now = self.net.sim.now
        if self.next < len(sent) and payload == sent[self.next]:
            self._accept(self.next, now)
            return
        if self.next > 0 and payload == sent[self.next - 1]:
            self.duplicates += 1
            return
        for j in range(self.next + 1, min(len(sent), self.next + self.LOOKAHEAD)):
            if payload == sent[j]:
                self.missing += j - self.next
                self._accept(j, now)
                return
        self.wrong += 1

    def _accept(self, index, now):
        self.correct += 1
        self.delays.append(now - self.source.created[index])
        self.next = index + 1
        self.last_delivery = now

    @property
    def done(self):
        total = self.source.finite_total
        return total is not None and self.next >= total
