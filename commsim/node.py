"""Nodes, the protocol interfaces, and the network that ties them together.

Layers inside one node (top to bottom):

    application   (traffic source at the sender, sink at the receiver)
    link layer    LinkProtocol: framing decisions, ACKs, retransmission   <- MM5, students
    MAC layer     MAC: when may a frame go on the shared medium?          <- MM6, students
    medium + PHY  collisions, propagation, bit errors                     (fixed)

Students only ever subclass `LinkProtocol` or `MAC`.
"""
from dataclasses import replace

import numpy as np

from .frames import ACK, DATA, Frame
from .sim import Simulator


# ====================================================================== student APIs

class LinkProtocol:
    """Base class for link-layer protocols (MM5).

    The framework creates one instance per peer and calls these methods.
    Every method gets `ctx`, your handle to the rest of the system:

        ctx.now                       current time in seconds
        ctx.params                    dict of scenario settings, e.g. ctx.params["timeout"]
        ctx.next_payload()            next bytes from the application, or None if none waiting
        ctx.send(frame)               transmit a Frame to the peer
        ctx.start_timer(name, sec)    on_timer(ctx, name) is called after `sec` seconds
                                      (counted from when the frame you just sent goes on air)
        ctx.cancel_timer(name)        stop a running timer
        ctx.deliver(payload)          hand received data to the application (receiver side)
        ctx.channel_busy()            True if another node is transmitting right now
    """

    def on_start(self, ctx):
        """Called once when the link to this peer is set up."""

    def on_data_ready(self, ctx):
        """Called when the application has new data waiting (see ctx.next_payload())."""

    def on_frame(self, ctx, frame: Frame):
        """Called for every frame from the peer whose preamble was recognised.
        Check frame.check_ok before trusting any field."""

    def on_timer(self, ctx, name):
        """Called when a timer started with ctx.start_timer(name, ...) expires."""


class MAC:
    """Base class for medium access control (MM6).

    Time on the shared medium is divided into slots. One slot fits one DATA frame
    plus the ACK that answers it. At the start of every slot in which the node has a
    frame waiting, the framework asks transmit_now(slot). At the end of a slot in
    which the node transmitted, it calls on_success(slot) if an ACK came back and
    on_failure(slot) otherwise. The node cannot tell a collision from a bit error.

    Available attributes:
        self.index      this node's number, 0 .. n_nodes-1
        self.n_nodes    number of nodes sharing the medium
        self.rng        random generator: self.rng.random(), self.rng.integers(a, b)
    """

    def __init__(self, index, n_nodes, rng):
        self.index = index
        self.n_nodes = n_nodes
        self.rng = rng

    def transmit_now(self, slot) -> bool:
        raise NotImplementedError

    def on_success(self, slot):
        pass

    def on_failure(self, slot):
        pass


# ====================================================================== framework

class PeerContext:
    """The `ctx` object handed to a LinkProtocol (one per node-peer pair)."""

    def __init__(self, node, peer, protocol):
        self._node = node
        self.peer = peer
        self.protocol = protocol
        self._timers = {}
        self._deferred = {}

    # time and settings
    @property
    def now(self):
        return self._node.net.sim.now

    @property
    def params(self):
        return self._node.net.params

    # sending
    def send(self, frame):
        frame = replace(frame, src=self._node.addr, dst=self.peer, check_ok=True)
        self._node._enqueue(frame, self)

    def next_payload(self):
        source = self._node.net.sources.get((self._node.addr, self.peer))
        return source.next_payload() if source else None

    def deliver(self, payload):
        sink = self._node.net.sinks.get((self._node.addr, self.peer))
        if sink is not None:
            sink.deliver(payload)

    def channel_busy(self):
        return self._node.net.medium.busy(self._node.addr)

    # timers
    def start_timer(self, name, duration):
        self.cancel_timer(name)
        if self._node._has_queued(self):
            self._deferred[name] = duration  # starts when our frame goes on air
        else:
            self._schedule(name, duration)

    def cancel_timer(self, name):
        self._deferred.pop(name, None)
        Simulator.cancel(self._timers.pop(name, None))

    def _schedule(self, name, duration):
        self._timers[name] = self._node.net.sim.schedule(duration, self._fire, name)

    def _fire(self, name):
        self._timers.pop(name, None)
        self.protocol.on_timer(self, name)

    def _frame_on_air(self):
        if not self._node._has_queued(self):
            for name, duration in self._deferred.items():
                self._schedule(name, duration)
            self._deferred.clear()


class Node:
    def __init__(self, net, addr, name, protocol_factory, mac=None, promiscuous=False):
        self.net = net
        self.addr = addr
        self.name = name
        self.factory = protocol_factory
        self.mac = mac
        self.promiscuous = promiscuous
        self.contexts = {}
        self.queue = []
        self.transmitting = False
        self.awaiting_ack = False
        self.tx_slot = None

    def context(self, peer):
        ctx = self.contexts.get(peer)
        if ctx is None:
            ctx = PeerContext(self, peer, self.factory())
            self.contexts[peer] = ctx
            ctx.protocol.on_start(ctx)
        return ctx

    # ---- sending side
    def _has_queued(self, ctx):
        return any(c is ctx for _, c in self.queue)

    def _enqueue(self, frame, ctx):
        self.queue.append((frame, ctx))
        self.net.count_tx(self, frame)
        if self.mac is None and not self.transmitting:
            self._start_next()

    def _start_next(self, slot=None):
        frame, ctx = self.queue.pop(0)
        self.transmitting = True
        self.net.medium.transmit(self, frame, slot)
        ctx._frame_on_air()

    def _tx_done(self):
        self.transmitting = False
        if self.mac is None and self.queue:
            self._start_next()

    # ---- receiving side
    def _receive(self, frame, tx):
        if not frame.check_ok:
            self.net.stats["detected_errors"] += 1
        if self.net.fmt.addr_bits == 0 or not frame.check_ok or frame.src not in self.net.nodes:
            frame.src, frame.dst = tx.sender, tx.dst
        if (self.mac is not None and self.awaiting_ack and frame.kind == ACK
                and frame.check_ok):
            self.awaiting_ack = False
            self.mac.on_success(self.tx_slot)
        if self.addr == frame.dst:
            ctx = self.context(frame.src)
            ctx.protocol.on_frame(ctx, frame)


class Network:
    """Holds the simulator, medium, nodes, traffic and statistics of one run."""

    def __init__(self, fmt, phy, rate_bps, prop_delay, seed=1, params=None, ack_loss=0.0):
        from .medium import Medium
        self.sim = Simulator()
        self.rng = np.random.default_rng(seed)
        self.fmt = fmt
        phy.rng = self.rng
        self.medium = Medium(self, phy, fmt, rate_bps, prop_delay, ack_loss)
        self.nodes = {}
        self.params = dict(params or {})
        self.sources = {}
        self.sinks = {}
        self.stats = {"data_tx": 0, "ack_tx": 0, "retransmissions": 0, "detected_errors": 0}
        self._sent_payloads = {}
        self.slot_time = None
        self.n_slots = 0

    def add_node(self, addr, name, protocol_factory, mac=None, promiscuous=False):
        node = Node(self, addr, name, protocol_factory, mac, promiscuous)
        self.nodes[addr] = node
        return node

    def count_tx(self, node, frame):
        if frame.kind == DATA:
            self.stats["data_tx"] += 1
            seen = self._sent_payloads.setdefault(node.addr, set())
            if frame.payload in seen:
                self.stats["retransmissions"] += 1
            else:
                seen.add(frame.payload)
        else:
            self.stats["ack_tx"] += 1

    # ---- slotted operation (MM6)
    def start_slots(self, slot_time, n_slots):
        self.slot_time = slot_time
        self.n_slots = n_slots
        self.sim.schedule(0.0, self._slot, 0, priority=10)

    def _slot(self, k):
        mac_nodes = [n for n in self.nodes.values() if n.mac is not None]
        for n in mac_nodes:
            if n.awaiting_ack:
                n.awaiting_ack = False
                n.mac.on_failure(n.tx_slot)
        if k >= self.n_slots:
            return
        for n in mac_nodes:
            if n.queue and not n.transmitting and n.mac.transmit_now(k):
                n.tx_slot = k
                n.awaiting_ack = True
                n._start_next(slot=k)
        self.at_slot(k + 1, self._slot, k + 1, priority=10)

    def at_slot(self, k, fn, *args, priority=5):
        """Run fn at the start of slot k (arrivals just before the MAC decisions)."""
        when = k * self.slot_time - (0 if priority >= 10 else 1e-9 * self.slot_time)
        self.sim.schedule(max(0.0, when - self.sim.now), fn, *args, priority=priority)
