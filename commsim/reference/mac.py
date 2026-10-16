"""MM6 reference solutions (instructors only; not handed out before the session)."""
from commsim import MAC


class AlwaysTransmit(MAC):
    def transmit_now(self, slot):
        return True


class RoundRobinTDMA(MAC):
    def transmit_now(self, slot):
        return slot % self.n_nodes == self.index


class SlottedAloha(MAC):
    def __init__(self, index, n_nodes, rng, p=0.1):
        super().__init__(index, n_nodes, rng)
        self.p = p

    def transmit_now(self, slot):
        return self.rng.random() < self.p


class GroupedAloha(MAC):
    def __init__(self, index, n_nodes, rng, group_a=4):
        super().__init__(index, n_nodes, rng)
        self.in_a = index < group_a
        size = group_a if self.in_a else n_nodes - group_a
        self.p = 1.0 / size

    def transmit_now(self, slot):
        my_slot = (slot % 2 == 0) if self.in_a else (slot % 2 == 1)
        return my_slot and self.rng.random() < self.p


class BackoffAloha(MAC):
    def __init__(self, index, n_nodes, rng):
        super().__init__(index, n_nodes, rng)
        self.failures = 0
        self.next_allowed = 0

    def transmit_now(self, slot):
        return slot >= self.next_allowed

    def on_success(self, slot):
        self.failures = 0

    def on_failure(self, slot):
        self.failures = min(self.failures + 1, 10)
        self.next_allowed = slot + 1 + int(self.rng.integers(0, 2 ** self.failures))


class MyMAC(MAC):
    """One possible challenge design: the busy streamer (last node) owns every even slot;
    everyone else uses back-off ALOHA in the odd slots. It meets the 90 % target, but
    plain back-off ALOHA still has a lower mean delay, so better designs exist."""

    def __init__(self, index, n_nodes, rng):
        super().__init__(index, n_nodes, rng)
        self.streamer = index == n_nodes - 1
        self.failures = 0
        self.next_allowed = 0

    def transmit_now(self, slot):
        if self.streamer:
            return slot % 2 == 0
        return slot % 2 == 1 and slot >= self.next_allowed

    def on_success(self, slot):
        self.failures = 0

    def on_failure(self, slot):
        if not self.streamer:
            self.failures = min(self.failures + 1, 10)
            self.next_allowed = slot + 1 + int(self.rng.integers(0, 2 ** self.failures))
