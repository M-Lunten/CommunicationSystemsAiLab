"""Flow control (MM8, Question 2): a fast sender and a receiver whose CPU is the bottleneck.

The sender puts 64-bit packets on a link (1 Gbit/s by default). The receiver must copy each
packet `copies` times, and every copy costs `instructions_per_copy` instructions on a CPU of
`mips` million instructions per second (Problem Set 4, Problem 3, as in its solution). Packets
wait in a receiver buffer of `buffer_packets`, which includes the packet being processed. A
packet that arrives at a full buffer is dropped.

With flow control, every time the receiver finishes a packet it sends the sender an update:
how many packets have arrived so far, and its advertised window,
advertised_window(buffer_size, queued). The update needs half the round trip to arrive. The
sender only sends while may_send(in_flight, window) allows it, where in_flight counts the
packets sent but not yet reported as arrived.
"""
import heapq
from dataclasses import dataclass, field


@dataclass
class FlowResults:
    scenario: str
    params: dict
    sent: int
    processed: int                  # packets the receiver finished
    dropped: int                    # packets that arrived at a full buffer
    max_queue: int                  # largest number of packets in the receiver buffer
    duration_ns: float              # from the first arrival to the last finished packet
    receiver_capacity_gbps: float   # what the receiver's CPU can handle
    trace: list = field(default_factory=list, repr=False)   # (time_ns, queue, event) for the start of the run

    @property
    def drop_fraction(self):
        return self.dropped / self.sent if self.sent else 0.0

    @property
    def goodput_gbps(self):
        """Processed packet bits per second, in Gbit/s."""
        bits = self.processed * self.params["packet_bits"]
        return bits / self.duration_ns if self.duration_ns else 0.0

    def summary(self):
        p = self.params
        return "\n".join([
            self.scenario,
            f"  receiver CPU         {p['copies']} copies x {p['instructions_per_copy']} instructions at "
            f"{p['mips']:g} MIPS = {self.params['processing_ns']:g} ns per packet",
            f"  receiver capacity    {self.receiver_capacity_gbps:.3g} Gbit/s   (link {p['link_gbps']:g} Gbit/s)",
            f"  packets sent         {self.sent}",
            f"  processed            {self.processed}",
            f"  dropped              {self.dropped}  ({100 * self.drop_fraction:.2f} %)",
            f"  fullest buffer       {self.max_queue} of {p['buffer_packets']} packets",
            f"  goodput              {self.goodput_gbps:.4f} Gbit/s"])

    def __str__(self):
        return self.summary()

    def _repr_pretty_(self, p, cycle):
        p.text(self.summary())


def flow_control_link(*, flow_control=None, copies=4, link_gbps=1.0, buffer_packets=64, rtt_us=0.0,
                      n_packets=200_000, packet_bits=64, instructions_per_copy=10, mips=1000,
                      trace_ns=40_000):
    """A sender sends `n_packets` packets to a receiver with a slow CPU.

    flow_control     None (send at the full link rate), or (advertised_window, may_send):
                     your two functions
    copies           how many times the receiver copies every packet
    link_gbps        link rate in Gbit/s
    buffer_packets   receiver buffer, including the packet being processed
    rtt_us           round-trip time in microseconds (data one way, window updates back)
    trace_ns         how much of the start of the run to keep for flow_plot
    """
    tx = packet_bits / link_gbps                       # ns on the link per packet
    proc = copies * instructions_per_copy * 1e3 / mips  # ns of CPU per packet
    half_rtt = rtt_us * 1e3 / 2
    if flow_control is not None:
        advertised_window, may_send = flow_control

    events, counter = [], 0

    def push(t, kind, data=None):
        nonlocal counter
        heapq.heappush(events, (t, counter, kind, data))
        counter += 1

    sent = acked = arrived = processed = dropped = queue = max_queue = 0
    window = advertised_window(buffer_packets, 0) if flow_control else None
    busy = False
    link_free_at = 0.0
    first_arrival = last_finish = None
    trace = []

    def note(t, what):
        if t <= trace_ns:
            trace.append((t, queue, what))

    def try_send(t):
        nonlocal sent, link_free_at
        if sent >= n_packets or link_free_at > t:
            return
        if flow_control is not None and not may_send(sent - acked, window):
            return
        sent += 1
        link_free_at = t + tx
        push(t + tx, "link free")
        push(t + tx + half_rtt, "arrive")

    push(0.0, "link free")
    while events:
        t, _, kind, data = heapq.heappop(events)
        if kind == "link free":
            try_send(t)
        elif kind == "arrive":
            arrived += 1
            if first_arrival is None:
                first_arrival = t
            if queue >= buffer_packets:
                dropped += 1
                note(t, "drop")
            else:
                queue += 1
                max_queue = max(max_queue, queue)
                note(t, "arrive")
                if not busy:
                    busy = True
                    push(t + proc, "finish")
        elif kind == "finish":
            queue -= 1
            processed += 1
            last_finish = t
            note(t, "finish")
            if queue:
                push(t + proc, "finish")
            else:
                busy = False
            if flow_control is not None:
                push(t + half_rtt, "update", (arrived, advertised_window(buffer_packets, queue)))
        elif kind == "update":
            acked, window = data
            try_send(t)

    params = dict(copies=copies, link_gbps=link_gbps, buffer_packets=buffer_packets, rtt_us=rtt_us,
                  n_packets=n_packets, packet_bits=packet_bits, instructions_per_copy=instructions_per_copy,
                  mips=mips, processing_ns=proc, flow_control=flow_control is not None)
    label = (f"flow_control_link: {'with' if flow_control else 'without'} flow control, {copies} copies, "
             f"link {link_gbps:g} Gbit/s, buffer {buffer_packets}, RTT {rtt_us:g} us, {n_packets} packets")
    duration = (last_finish - first_arrival) if processed else 0.0
    return FlowResults(label, params, sent, processed, dropped, max_queue, duration,
                       packet_bits / proc, trace)
