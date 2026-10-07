"""The shared medium: the wire or the air that all nodes transmit on.

* A transmission takes  (frame bits / rate)  seconds and arrives `prop_delay` later.
* If two transmissions from different nodes overlap in time, both are destroyed
  at the receiver (a collision).
* A node cannot receive while it is transmitting itself (half duplex, as in the
  TDD link of Lecture 5).
* Surviving bits pass through the physical layer (bit errors), then the receiver
  parses them. A broken preamble means the frame is not noticed at all.
"""
from dataclasses import dataclass, replace

from .frames import ACK


@dataclass
class Transmission:
    sender: int
    dst: int
    frame: object
    bits: object
    t0: float
    t1: float
    slot: int = None
    outcome: str = "pending"   # ok | error | collision | lost


class Medium:
    def __init__(self, net, phy, fmt, rate_bps, prop_delay, ack_loss=0.0):
        self.net = net
        self.phy = phy
        self.fmt = fmt
        self.rate = float(rate_bps)
        self.prop = float(prop_delay)
        self.ack_loss = float(ack_loss)
        self.log = []
        self._recent = []
        self._max_dur = 0.0

    def transmit(self, node, frame, slot=None):
        sim = self.net.sim
        bits = self.fmt.encode(frame)
        frame.nbits = int(bits.size)
        dur = bits.size / self.rate
        self._max_dur = max(self._max_dur, dur)
        tx = Transmission(node.addr, frame.dst, replace(frame), bits, sim.now, sim.now + dur, slot)
        self.log.append(tx)
        self._recent.append(tx)
        sim.schedule(dur, node._tx_done)
        sim.schedule(dur + self.prop, self._arrive, tx)
        return tx

    def busy(self, addr):
        """True if some other node's signal is arriving at `addr` right now (carrier sensing)."""
        now = self.net.sim.now
        return any(o.sender != addr and o.t0 + self.prop <= now < o.t1 + self.prop
                   for o in self._recent)

    def _arrive(self, tx):
        now = self.net.sim.now
        horizon = now - self.prop - 2 * self._max_dur
        self._recent = [o for o in self._recent if o.t1 >= horizon]
        collided = any(o is not tx and o.sender != tx.sender and o.t0 < tx.t1 and tx.t0 < o.t1
                       for o in self._recent)
        receivers = [n for n in self.net.nodes.values()
                     if n.addr != tx.sender and (n.addr == tx.dst or n.promiscuous)]
        for node in receivers:
            outcome = self._receive_at(node, tx, collided)
            if node.addr == tx.dst:
                tx.outcome = outcome
        if tx.outcome == "pending":
            tx.outcome = "lost"

    def _receive_at(self, node, tx, collided):
        if collided:
            return "collision"
        a0, a1 = tx.t0 + self.prop, tx.t1 + self.prop
        if any(o.sender == node.addr and o.t0 < a1 and a0 < o.t1 for o in self._recent):
            return "lost"  # receiver was busy transmitting
        if tx.frame.kind == ACK and self.ack_loss and self.net.rng.random() < self.ack_loss:
            return "lost"
        frame = self.fmt.decode(self.phy.corrupt(tx.bits))
        if frame is None:
            return "lost"  # preamble not recognised
        node._receive(frame, tx)
        return "ok" if frame.check_ok else "error"
