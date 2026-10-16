"""MM6 - your medium access control (MAC).

This is the only file you change in the MM6 lab (together with the lab notebook).

Below the MAC, the shared channel is divided into slots; one slot fits one DATA frame
and its ACK. Above the MAC runs the stop-and-wait link layer from MM5: if a frame is
not ACKed, the link layer hands it to you again.

A MAC answers one question at the start of every slot in which its node has a frame
waiting: transmit_now(slot) -> True or False. Afterwards it hears how it went:
on_success(slot) when the ACK came back, on_failure(slot) when it did not.
(A node cannot tell a collision from a bit error.)

STATUS IN THIS EXAMPLE: solved. This is what a group's file could look like at the
end of the MM6 session. What students were handed at the start is kept in
instructor/starters/mm6_mac.py.

Available in every MAC:
    self.index     this node's number, 0 .. n_nodes-1
    self.n_nodes   number of nodes sharing the channel
    self.rng       random numbers: self.rng.random() in [0, 1), self.rng.integers(a, b)
"""
from commsim import MAC


# =============================================================================
# Given examples
# =============================================================================

class AlwaysTransmit(MAC):
    """What the MM5 link layer does on its own: transmit whenever it has a frame."""

    def transmit_now(self, slot):
        return True


class RoundRobinTDMA(MAC):
    """Scheduled access (Lecture 6): node i owns every slot with slot % n_nodes == i."""

    def transmit_now(self, slot):
        return slot % self.n_nodes == self.index


# =============================================================================
# Part B: slotted ALOHA
# =============================================================================

class SlottedAloha(MAC):
    """In every slot in which it has a frame, transmit with probability p."""

    def __init__(self, index, n_nodes, rng, p=0.1):
        super().__init__(index, n_nodes, rng)
        self.p = p

    def transmit_now(self, slot):
        # An independent coin flip in every slot: no memory of earlier slots.
        return self.rng.random() < self.p


# =============================================================================
# Part C2: TDMA + ALOHA in groups (Problem Set 2, Problem 2c)
# =============================================================================

class GroupedAloha(MAC):
    """The first `group_a` nodes form group A and may only use even slots.
    The remaining nodes form group B and may only use odd slots.
    Inside its group, a node transmits with probability 1 / (size of its group)."""

    def __init__(self, index, n_nodes, rng, group_a=4):
        super().__init__(index, n_nodes, rng)
        self.group_a = group_a
        self.in_a = index < group_a
        group_size = group_a if self.in_a else n_nodes - group_a
        self.p = 1.0 / group_size           # optimal p inside the group (Lecture 6)

    def transmit_now(self, slot):
        my_slot = (slot % 2 == 0) if self.in_a else (slot % 2 == 1)   # TDMA between groups
        return my_slot and self.rng.random() < self.p                 # ALOHA inside a group


# =============================================================================
# Part C3 (if time): binary exponential back-off
# =============================================================================

class BackoffAloha(MAC):
    """Transmit as soon as possible. After the k-th failure in a row, wait a random
    number of slots between 0 and 2**k - 1 before trying again (cap k at 10).
    After a success, start again from k = 0."""

    def __init__(self, index, n_nodes, rng):
        super().__init__(index, n_nodes, rng)
        self.failures = 0           # k: failures in a row
        self.next_allowed = 0       # first slot in which we may try again

    def transmit_now(self, slot):
        return slot >= self.next_allowed

    def on_success(self, slot):
        self.failures = 0

    def on_failure(self, slot):
        self.failures = min(self.failures + 1, 10)
        wait = int(self.rng.integers(0, 2 ** self.failures))     # 0 .. 2**k - 1 slots
        self.next_allowed = slot + 1 + wait


# =============================================================================
# Challenge (optional, at home): design your own MAC
# =============================================================================

class MyMAC(MAC):
    """Our design: the streamer (last node) owns every even slot; everyone else uses
    back-off ALOHA in the odd slots."""

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
