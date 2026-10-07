"""Results of one simulation run, with the metrics used in the course."""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Results:
    scenario: str
    duration: float                 # seconds simulated (until the last delivery for file transfers)
    payload_bytes: int
    data_frames_sent: int
    retransmissions: int
    ack_frames_sent: int
    detected_errors: int            # frames whose error check failed at the receiver
    delivered: int                  # payloads delivered correctly, in order
    duplicates: int                 # payloads delivered more than once
    undetected_errors: int          # corrupted payloads handed to the application
    offered: int                    # payloads the applications produced
    mean_delay: float               # seconds from creation to correct delivery
    per_user: dict = field(default_factory=dict)          # payloads delivered per sender
    per_user_offered: dict = field(default_factory=dict)  # payloads produced per sender
    slots: dict = field(default_factory=dict)
    net: object = field(default=None, repr=False)

    @property
    def not_delivered(self):
        """Payloads that never reached the receiver intact."""
        return self.offered - self.delivered

    # ---- link metrics (Lecture 5)
    @property
    def goodput_bps(self):
        """Useful payload bits delivered correctly per second."""
        return self.delivered * 8 * self.payload_bytes / self.duration if self.duration else 0.0

    @property
    def rate_bps(self):
        return self.net.medium.rate

    @property
    def utilisation(self):
        """Goodput as a fraction of the channel's raw bit rate."""
        return self.goodput_bps / self.rate_bps

    # ---- multiuser metrics (Lecture 6)
    @property
    def throughput(self):
        """Successful slots per slot (packets/slot)."""
        n = self.slots.get("total", 0)
        return self.slots.get("success", 0) / n if n else float("nan")

    @property
    def fairness(self):
        """Jain's fairness index over users' delivered packets: 1 = equal, 1/n = one user gets all."""
        x = np.array(list(self.per_user.values()), dtype=float)
        return float(x.sum() ** 2 / (len(x) * (x ** 2).sum())) if x.size and x.any() else float("nan")

    def summary(self):
        lines = [f"{self.scenario}",
                 f"  time simulated       {self.duration:.4g} s",
                 f"  data frames sent     {self.data_frames_sent}  (of which retransmissions: {self.retransmissions})",
                 f"  ACK frames sent      {self.ack_frames_sent}",
                 f"  failed error check   {self.detected_errors}  (frames)",
                 f"  delivered correctly  {self.delivered} of {self.offered} offered",
                 f"  duplicates           {self.duplicates}",
                 f"  undetected errors    {self.undetected_errors}",
                 f"  never delivered      {self.not_delivered}",
                 f"  goodput              {self.goodput_bps:.4g} bit/s  ({100 * self.utilisation:.1f} % of the link rate)",
                 f"  mean delay           {self.mean_delay:.4g} s"]
        if self.slots:
            s = self.slots
            lines += [f"  slots                {s['total']}: {s['success']} success, {s['collision']} collision, "
                      f"{s['idle']} idle, {s['error']} bit-error",
                      f"  throughput           {self.throughput:.3f} packets/slot",
                      f"  fairness (Jain)      {self.fairness:.3f}",
                      "  per user             " + ", ".join(f"{k}: {v}" for k, v in self.per_user.items())]
        return "\n".join(lines)

    def __str__(self):
        return self.summary()

    def _repr_pretty_(self, p, cycle):
        p.text(self.summary())


def collect(net, scenario, payload_bytes, duration, user_names=None):
    sinks = list(net.sinks.values())
    delays = [d for s in sinks for d in s.delays]
    per_user, per_user_offered = {}, {}
    for (rx, tx_addr), sink in net.sinks.items():
        name = net.nodes[tx_addr].name
        per_user[name] = per_user.get(name, 0) + sink.correct
        per_user_offered[name] = per_user_offered.get(name, 0) + len(sink.source.payloads)
    slots = {}
    if net.n_slots:
        counts = np.zeros(net.n_slots, dtype=int)
        status = {}
        for tx in net.medium.log:
            if tx.slot is not None and tx.slot < net.n_slots:
                counts[tx.slot] += 1
                status[tx.slot] = tx.outcome
        success = sum(1 for k, c in enumerate(counts) if c == 1 and status.get(k) == "ok")
        error = sum(1 for k, c in enumerate(counts) if c == 1 and status.get(k) != "ok")
        slots = {"total": net.n_slots, "idle": int((counts == 0).sum()), "success": success,
                 "collision": int((counts >= 2).sum()), "error": error}
    return Results(
        scenario=scenario, duration=duration, payload_bytes=payload_bytes,
        data_frames_sent=net.stats["data_tx"], retransmissions=net.stats["retransmissions"],
        ack_frames_sent=net.stats["ack_tx"], detected_errors=net.stats["detected_errors"],
        delivered=sum(s.correct for s in sinks), duplicates=sum(s.duplicates for s in sinks),
        undetected_errors=sum(s.wrong for s in sinks),
        offered=sum(len(s.source.payloads) for s in sinks),
        mean_delay=float(np.mean(delays)) if delays else float("nan"),
        per_user=per_user, per_user_offered=per_user_offered, slots=slots, net=net)
