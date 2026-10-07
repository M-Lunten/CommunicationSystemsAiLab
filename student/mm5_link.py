"""MM5 - your link layer.

This is the only file you change in the MM5 lab (together with the lab notebook).
The rest of the framework (commsim/) is fixed.

STATUS IN THIS EXAMPLE: solved. This is what a group's file could look like at the
end of the MM5 session. What students were handed at the start is kept in
instructor/starters/mm5_link.py.
"""
from commsim import ACK, DATA, Frame, LinkProtocol


# =============================================================================
# Given example: "Utopia". Send everything at once, trust everything you receive.
# =============================================================================

class UtopiaSender(LinkProtocol):
    def on_start(self, ctx):
        self._send_all(ctx)

    def on_data_ready(self, ctx):
        self._send_all(ctx)

    def _send_all(self, ctx):
        payload = ctx.next_payload()
        while payload is not None:
            ctx.send(Frame(kind=DATA, payload=payload))
            payload = ctx.next_payload()


class UtopiaReceiver(LinkProtocol):
    def on_frame(self, ctx, frame):
        if frame.kind == DATA:
            ctx.deliver(frame.payload)


# =============================================================================
# Part B: stop-and-wait ARQ with a 1-bit sequence number (implemented with Copilot)
# =============================================================================

class StopAndWaitSender(LinkProtocol):
    """Send one DATA frame, wait for its ACK, retransmit on timeout."""

    def on_start(self, ctx):
        self.seq = 0            # sequence bit of the frame currently being sent
        self.current = None     # payload waiting for an ACK (None = idle)
        self._send_next(ctx)

    def on_data_ready(self, ctx):
        if self.current is None:          # only start something new when idle
            self._send_next(ctx)

    def _send_next(self, ctx):
        self.current = ctx.next_payload()
        if self.current is not None:
            self._transmit(ctx)

    def _transmit(self, ctx):
        ctx.send(Frame(kind=DATA, seq=self.seq, payload=self.current))
        ctx.start_timer("retransmit", ctx.params["timeout"])

    def on_frame(self, ctx, frame):
        if not frame.check_ok or frame.kind != ACK or self.current is None:
            return
        # Bob's ACK says which sequence bit he expects next.
        if frame.ack == (self.seq + 1) % 2:
            ctx.cancel_timer("retransmit")
            self.seq = (self.seq + 1) % 2
            self._send_next(ctx)
        # An ACK that still asks for self.seq is stale: ignore it, the timer handles it.

    def on_timer(self, ctx, name):
        if name == "retransmit" and self.current is not None:
            self._transmit(ctx)           # no ACK in time: send the same frame again


class StopAndWaitReceiver(LinkProtocol):
    """Deliver each new frame once; ACK everything that arrives intact."""

    def on_start(self, ctx):
        self.expected = 0       # sequence bit of the next new frame

    def on_frame(self, ctx, frame):
        if not frame.check_ok or frame.kind != DATA:
            return              # corrupted: stay silent, the sender's timer will fire
        if frame.seq == self.expected:
            ctx.deliver(frame.payload)
            self.expected = (self.expected + 1) % 2
        # A copy (seq != expected) is not delivered again, but it is ACKed again,
        # because the previous ACK was obviously lost.
        ctx.send(Frame(kind=ACK, ack=self.expected))
