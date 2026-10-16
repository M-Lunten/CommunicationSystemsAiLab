"""Reliability at two layers (MM7, Part B): a Higher Layer (HL) on top of a Lower Layer (LL).

Zoya's HL sends packets to Yoshi's HL. Below each HL is an LL that carries the packets
over one link. ACKs, timeouts and retransmissions can be switched on at the LL, at the
HL, or at both (Lecture 7, Example 1; Problem Set 7, Problem 2):

    reliability="LL"     the LL does ARQ, the HL just hands packets down (reliable service)
    reliability="HL"     the LL sends every frame once, without ACKs; the HL does ARQ
    reliability="both"   both layers do ARQ, independently of each other
    reliability="none"   nobody does

Time runs in slots. In each slot, each direction of the link carries one LL data frame,
and a short LL ACK can go back on the feedback channel at the same time. A frame sent in
slot t arrives at the start of slot t + 1, so one LL attempt (DATA out, ACK back) takes
2 slots. The HL's ACKs are ordinary data for Yoshi's LL.

The channel is a packet erasure channel: every frame (DATA or ACK, in either direction)
is lost with probability `per`. Which slots are bad is drawn once from `seed`, so runs
with different protocol settings face the same channel realisation.

Both layers decide about retransmissions with the same rule, which the student writes:
retry_decision(waited, retransmissions, timeout, max_retransmissions) -> "wait",
"retransmit" or "give_up".
"""
import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

WAIT, RETRANSMIT, GIVE_UP = "wait", "retransmit", "give_up"
RELIABILITY = ("LL", "HL", "both", "none")

# Header sizes in bits
LL_FRAMING_BITS = 8          # every LL frame: start flag / frame type
SEQ_BITS = 8                 # sequence number, at the LL or HL when that layer does ARQ
CHECK_BITS = 16              # error check (CRC-16), at the LL or HL when that layer does ARQ
LL_ACK_BITS = LL_FRAMING_BITS + SEQ_BITS + CHECK_BITS


def normalise_decision(value):
    """Map what a retry rule returned to WAIT, RETRANSMIT or GIVE_UP (None if invalid)."""
    if not isinstance(value, str):
        return None
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    v = {"giveup": GIVE_UP}.get(v, v)
    return v if v in (WAIT, RETRANSMIT, GIVE_UP) else None


class PacketErasureChannel:
    """Every frame is lost with probability `per`. Bad slots are fixed by `seed`."""

    STREAMS = ("data Zoya>Yoshi", "data Yoshi>Zoya", "ack Zoya>Yoshi", "ack Yoshi>Zoya")

    def __init__(self, per, seed=1):
        if not 0.0 <= per <= 1.0:
            raise ValueError("per must be between 0 and 1")
        self.per = float(per)
        self._rngs = {s: np.random.default_rng([seed, i]) for i, s in enumerate(self.STREAMS)}
        self._bad = {s: np.zeros(0, dtype=bool) for s in self.STREAMS}

    def lost(self, stream, slot):
        bad = self._bad[stream]
        if slot >= bad.size:
            more = self._rngs[stream].random(max(1024, slot + 1 - bad.size)) < self.per
            bad = self._bad[stream] = np.concatenate([bad, more])
        return bool(bad[slot])


@dataclass(frozen=True)
class HLPacket:
    kind: str        # "DATA" or "ACK"
    seq: int         # HL sequence number (= packet number)
    copy: int = 0    # 0 = the HL's first transmission, 1 = its first retransmission, ...

    @property
    def label(self):
        return f"A{self.seq}" if self.kind == "ACK" else f"{self.seq}" + "'" * self.copy


@dataclass
class Event:
    slot: int
    row: str         # "Zoya HL", "Zoya LL", "Yoshi LL", "Yoshi HL"
    kind: str
    label: str = ""


class _Pending:
    """An LL frame that is waiting for its ACK."""

    def __init__(self, packet, ll_seq):
        self.packet, self.ll_seq = packet, ll_seq
        self.sent_at, self.retransmissions, self.resend = None, 0, True


class _LowerLayer:
    def __init__(self, reliable):
        self.reliable = reliable
        self.queue = deque()      # HL packets waiting to be sent
        self.current = None       # _Pending (reliable LL only)
        self.next_seq = 0
        self.last_rx_seq = -1     # receiver side: highest LL sequence number passed up
        self.acks_to_send = []

    def busy(self):
        return self.current is not None or bool(self.queue)

    def holds(self, seq):
        """True if an HL DATA packet with this sequence number is still in this LL."""
        packets = list(self.queue) + ([self.current.packet] if self.current else [])
        return any(p.kind == "DATA" and p.seq == seq for p in packets)


class _TwoLayerLink:
    def __init__(self, retry, reliability, per, k_ll, t_ll, k_hl, t_hl, n_packets,
                 payload_bytes, n_apps, seed, max_slots):
        if reliability not in RELIABILITY:
            raise ValueError(f"reliability must be one of {RELIABILITY}")
        self.retry = retry
        self.reliability = reliability
        self.ll_reliable = reliability in ("LL", "both")
        self.hl_reliable = reliability in ("HL", "both")
        self.k_ll, self.t_ll, self.k_hl, self.t_hl = k_ll, t_ll, k_hl, t_hl
        self.n_packets, self.payload_bytes = n_packets, payload_bytes
        self.channel = PacketErasureChannel(per, seed)
        self.max_slots = max_slots
        self.ll = {"Zoya": _LowerLayer(self.ll_reliable), "Yoshi": _LowerLayer(self.ll_reliable)}
        self.peer = {"Zoya": "Yoshi", "Yoshi": "Zoya"}

        self.app_id_bits = math.ceil(math.log2(n_apps)) if n_apps > 1 else 0
        hl_arq = SEQ_BITS + CHECK_BITS if self.hl_reliable else 0
        self.bits = {"HL header": self.app_id_bits + hl_arq,
                     "HL ACK": self.app_id_bits + SEQ_BITS + CHECK_BITS,
                     "LL header": LL_FRAMING_BITS + (SEQ_BITS + CHECK_BITS if self.ll_reliable else 0),
                     "LL ACK": LL_ACK_BITS}

        self.now = 0
        self.in_flight = []
        self.events = []
        self.next_new = 0
        self.outstanding = None          # Zoya's HL: [seq, copy, handed_at, retransmissions]
        self.created = {}
        self.delivered_at = {}
        self.received_copies = {}
        self.hl_retx_log = []            # (seq, copy, premature)
        self.c = dict(ll_transmissions=0, ll_retransmissions=0, ll_acks=0, ll_give_ups=0,
                      hl_transmissions=0, hl_give_ups=0, duplicates=0, bits_on_air=0)

    # ------------------------------------------------------------------ helpers
    def _log(self, row, kind, label=""):
        self.events.append(Event(self.now, row, kind, label))

    def _decide(self, waited, retransmissions, timeout, limit, layer):
        raw = self.retry(waited, retransmissions, timeout, limit)
        d = normalise_decision(raw)
        if d is None:
            raise ValueError(f"retry_decision returned {raw!r} (for the {layer}); it must return "
                             f"'{WAIT}', '{RETRANSMIT}' or '{GIVE_UP}'")
        return d

    def _packet_bits(self, p):
        if p.kind == "ACK":
            return self.bits["HL ACK"]
        return 8 * self.payload_bytes + self.bits["HL header"]

    # ------------------------------------------------------------------ higher layer
    def _hand_down(self, seq, copy):
        self.ll["Zoya"].queue.append(HLPacket("DATA", seq, copy))
        self.c["hl_transmissions"] += 1

    def _hl_timer(self):
        out = self.outstanding
        if out is None:
            return
        seq, copy, handed_at, retx = out
        d = self._decide(self.now - handed_at, retx, self.t_hl, self.k_hl, "HL")
        if d == RETRANSMIT:
            premature = self.ll["Zoya"].holds(seq)
            self.outstanding = [seq, copy + 1, self.now, retx + 1]
            self.hl_retx_log.append((seq, copy + 1, premature))
            self._hand_down(seq, copy + 1)
            self._log("Zoya HL", "hl_retx_premature" if premature else "hl_retx",
                      HLPacket("DATA", seq, copy + 1).label)
        elif d == GIVE_UP:
            self.outstanding = None
            self.c["hl_give_ups"] += 1
            self._log("Zoya HL", "hl_give_up", str(seq))

    def _hl_feed(self):
        if self.next_new >= self.n_packets:
            return
        if self.hl_reliable:
            if self.outstanding is not None:
                return
        elif self.ll["Zoya"].busy():
            return
        seq = self.next_new
        self.next_new += 1
        self.created[seq] = self.now
        self._hand_down(seq, 0)
        if self.hl_reliable:
            self.outstanding = [seq, 0, self.now, 0]
        self._log("Zoya HL", "hl_send", str(seq))

    def _hl_receive(self, node, p):
        if node == "Yoshi" and p.kind == "DATA":
            self.received_copies.setdefault(p.seq, set()).add(p.copy)
            if self.hl_reliable:
                self.ll["Yoshi"].queue.append(HLPacket("ACK", p.seq))
            if p.seq in self.delivered_at:
                self.c["duplicates"] += 1
                self._log("Yoshi HL", "duplicate", p.label)
            else:
                self.delivered_at[p.seq] = self.now
                self._log("Yoshi HL", "deliver", p.label)
        elif node == "Zoya" and p.kind == "ACK":
            if self.outstanding is not None and self.outstanding[0] == p.seq:
                self.outstanding = None
                self._log("Zoya HL", "hl_ack", p.label)

    # ------------------------------------------------------------------ lower layer
    def _arrive(self, frame):
        kind, src, dst, ll_seq, packet = frame
        ll = self.ll[dst]
        if kind == "ack":
            sender = self.ll[dst]
            if sender.current is not None and sender.current.ll_seq == ll_seq:
                sender.current = None
                self._log(f"{dst} LL", "ll_ack", "")
            return
        if ll.reliable:
            ll.acks_to_send.append(ll_seq)
            if ll_seq <= ll.last_rx_seq:
                return                      # LL duplicate: ACK again, don't pass up
            ll.last_rx_seq = ll_seq
        self._hl_receive(dst, packet)

    def _ll_timer(self, node):
        ll = self.ll[node]
        cur = ll.current
        if not ll.reliable or cur is None or cur.resend:
            return
        d = self._decide(self.now - cur.sent_at, cur.retransmissions, self.t_ll, self.k_ll, "LL")
        if d == RETRANSMIT:
            cur.retransmissions += 1
            cur.resend = True
        elif d == GIVE_UP:
            ll.current = None
            self.c["ll_give_ups"] += 1
            self._log(f"{node} LL", "ll_give_up", cur.packet.label)

    def _send_frame(self, node, packet, ll_seq, retransmission):
        peer = self.peer[node]
        self.c["ll_transmissions"] += 1
        self.c["ll_retransmissions"] += int(retransmission)
        self.c["bits_on_air"] += self.bits["LL header"] + self._packet_bits(packet)
        lost = self.channel.lost(f"data {node}>{peer}", self.now)
        self._log(f"{node} LL", "tx_lost" if lost else "tx_ok", packet.label)
        if not lost:
            self.in_flight.append(("data", node, peer, ll_seq, packet))

    def _ll_transmit(self, node):
        ll, peer = self.ll[node], self.peer[node]
        for ack in ll.acks_to_send:
            self.c["ll_acks"] += 1
            self.c["bits_on_air"] += self.bits["LL ACK"]
            lost = self.channel.lost(f"ack {node}>{peer}", self.now)
            self._log(f"{node} LL", "ack_lost" if lost else "ack_ok")
            if not lost:
                self.in_flight.append(("ack", node, peer, ack, None))
        ll.acks_to_send = []
        if ll.reliable:
            if ll.current is None and ll.queue:
                ll.current = _Pending(ll.queue.popleft(), ll.next_seq)
                ll.next_seq += 1
            cur = ll.current
            if cur is not None and cur.resend:
                cur.resend = False
                cur.sent_at = self.now
                self._send_frame(node, cur.packet, cur.ll_seq, cur.retransmissions > 0)
        elif ll.queue:
            self._send_frame(node, ll.queue.popleft(), ll.next_seq, False)
            ll.next_seq += 1

    # ------------------------------------------------------------------ main loop
    def _finished(self):
        return (self.next_new >= self.n_packets and self.outstanding is None
                and not self.in_flight and not any(ll.busy() or ll.acks_to_send
                                                   for ll in self.ll.values()))

    def run(self):
        for t in range(self.max_slots):
            self.now = t
            arrivals, self.in_flight = self.in_flight, []
            for frame in arrivals:
                self._arrive(frame)
            for node in ("Zoya", "Yoshi"):
                self._ll_timer(node)
            if self.hl_reliable:
                self._hl_timer()
            self._hl_feed()
            for node in ("Zoya", "Yoshi"):
                self._ll_transmit(node)
            if self._finished():
                return t + 1
        return self.max_slots


@dataclass
class LayerResults:
    scenario: str
    params: dict
    slots: int                  # slots until everything was finished
    offered: int                # packets Zoya's HL had to send
    delivered: int              # packets that reached Yoshi's application (each counted once)
    ll_transmissions: int       # LL data frames sent, both directions (incl. frames carrying HL ACKs)
    ll_retransmissions: int     # ... of which LL retransmissions
    ll_acks: int                # LL ACK frames sent
    ll_give_ups: int            # times an LL gave up on a frame and reported a failure
    hl_transmissions: int       # packets Zoya's HL handed down (incl. HL retransmissions)
    hl_retransmissions: int
    hl_premature: int           # HL retransmissions while Zoya's LL still held an earlier copy
    hl_unnecessary: int         # HL retransmissions of a packet whose earlier copy reached Yoshi anyway
    hl_give_ups: int
    duplicates: int             # copies Yoshi's HL received again (and threw away)
    mean_delay: float           # slots from handing a packet down to delivery at Yoshi
    bits_on_air: int            # all bits sent on the channel, lost frames included
    header_bits: dict = field(default_factory=dict)
    events: list = field(default_factory=list, repr=False)

    @property
    def reliability(self):
        """Fraction of the packets that reached Yoshi's application."""
        return self.delivered / self.offered if self.offered else float("nan")

    @property
    def goodput(self):
        """Application bits delivered per slot."""
        return self.delivered * 8 * self.params["payload_bytes"] / self.slots if self.slots else 0.0

    @property
    def efficiency(self):
        """Fraction of the bits sent on the channel that are delivered application data."""
        payload = self.delivered * 8 * self.params["payload_bytes"]
        return payload / self.bits_on_air if self.bits_on_air else float("nan")

    def summary(self):
        h = self.header_bits
        return "\n".join([
            self.scenario,
            f"  header bits          HL {h['HL header']}, LL {h['LL header']} per frame;"
            f" HL ACK {h['HL ACK']}, LL ACK {h['LL ACK']}",
            f"  slots used           {self.slots}",
            f"  delivered            {self.delivered} of {self.offered}  (reliability {self.reliability:.3f})",
            f"  LL transmissions     {self.ll_transmissions}  (of which retransmissions: {self.ll_retransmissions})",
            f"  LL ACKs sent         {self.ll_acks}",
            f"  LL gave up           {self.ll_give_ups}",
            f"  HL transmissions     {self.hl_transmissions}  (of which retransmissions: {self.hl_retransmissions};"
            f" premature: {self.hl_premature}, unnecessary: {self.hl_unnecessary})",
            f"  HL gave up           {self.hl_give_ups}",
            f"  duplicates at Yoshi  {self.duplicates}",
            f"  mean delay           {self.mean_delay:.2f} slots",
            f"  goodput              {self.goodput:.1f} bits/slot",
            f"  efficiency           {self.efficiency:.3f}  (delivered application bits / all bits sent)"])

    def __str__(self):
        return self.summary()

    def _repr_pretty_(self, p, cycle):
        p.text(self.summary())


def two_layer_link(retry, *, reliability="LL", per=0.2, k_ll=2, t_ll=2, k_hl=2, t_hl=8,
                   n_packets=100, payload_bytes=100, n_apps=16, seed=7, max_slots=None):
    """Zoya's HL sends `n_packets` packets to Yoshi's HL over one LL link.

    retry         your retry_decision(waited, retransmissions, timeout, max_retransmissions)
    reliability   "LL", "HL", "both" or "none": which layers use ACKs, timeouts and retransmissions
    per           packet error probability: every frame (DATA or ACK) is lost with this probability
    k_ll, t_ll    LL: maximum number of retransmissions, timeout in slots
    k_hl, t_hl    HL: maximum number of retransmissions, timeout in slots
    payload_bytes application data per packet
    n_apps        number of applications that share the HL (sets the size of the app id field)
    seed          fixes which slots are bad; the same seed gives the same channel

    With the default timing, one LL attempt (DATA out, ACK back) takes 2 slots.
    Returns LayerResults: print it, or draw it with layer_timeline(results).
    """
    if max_slots is None:
        max_slots = 1000 + 50 * n_packets * (k_hl + 1) * (k_ll + 1) * max(2, t_ll)
    sim = _TwoLayerLink(retry, reliability, per, k_ll, t_ll, k_hl, t_hl, n_packets,
                        payload_bytes, n_apps, seed, max_slots)
    slots = sim.run()
    unnecessary = sum(1 for seq, copy, _ in sim.hl_retx_log
                      if any(c < copy for c in sim.received_copies.get(seq, ())))
    delays = [sim.delivered_at[s] - sim.created[s] for s in sim.delivered_at]
    params = dict(reliability=reliability, per=per, k_ll=k_ll, t_ll=t_ll, k_hl=k_hl, t_hl=t_hl,
                  n_packets=n_packets, payload_bytes=payload_bytes, n_apps=n_apps, seed=seed)
    parts = [f"reliability={reliability}", f"PER={per:g}"]
    if sim.ll_reliable:
        parts.append(f"K_LL={k_ll}, T_LL={t_ll}")
    if sim.hl_reliable:
        parts.append(f"K_HL={k_hl}, T_HL={t_hl}")
    label = f"two_layer_link: {', '.join(parts)}, {n_packets} x {payload_bytes} B, seed {seed}"
    if slots >= max_slots:
        label += "  [stopped at max_slots: does your retry rule ever give up?]"
    c = sim.c
    return LayerResults(
        scenario=label, params=params, slots=slots, offered=n_packets,
        delivered=len(sim.delivered_at), ll_transmissions=c["ll_transmissions"],
        ll_retransmissions=c["ll_retransmissions"], ll_acks=c["ll_acks"],
        ll_give_ups=c["ll_give_ups"], hl_transmissions=c["hl_transmissions"],
        hl_retransmissions=len(sim.hl_retx_log),
        hl_premature=sum(1 for *_, p in sim.hl_retx_log if p), hl_unnecessary=unnecessary,
        hl_give_ups=c["hl_give_ups"], duplicates=c["duplicates"],
        mean_delay=float(np.mean(delays)) if delays else float("nan"),
        bits_on_air=c["bits_on_air"], header_bits=dict(sim.bits), events=sim.events)


def compare_runs(runs):
    """Print the main metrics of several runs side by side. `runs` is {label: LayerResults}."""
    rows = [("delivered", lambda r: f"{r.delivered}/{r.offered}"),
            ("LL transmissions", lambda r: r.ll_transmissions),
            ("LL retransmissions", lambda r: r.ll_retransmissions),
            ("LL ACKs", lambda r: r.ll_acks),
            ("HL retransmissions", lambda r: r.hl_retransmissions),
            ("  premature", lambda r: r.hl_premature),
            ("  unnecessary", lambda r: r.hl_unnecessary),
            ("duplicates at Yoshi", lambda r: r.duplicates),
            ("mean delay (slots)", lambda r: f"{r.mean_delay:.2f}"),
            ("goodput (bits/slot)", lambda r: f"{r.goodput:.1f}"),
            ("efficiency", lambda r: f"{r.efficiency:.3f}")]
    width = max(12, *(len(k) + 2 for k in runs))
    lines = [f"{'':<22}" + "".join(f"{k:>{width}}" for k in runs)]
    for name, fn in rows:
        lines.append(f"{name:<22}" + "".join(f"{str(fn(r)):>{width}}" for r in runs.values()))
    print("\n".join(lines))
