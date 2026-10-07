"""Reference stop-and-wait ARQ with a 1-bit sequence number (Lecture 5).

Released after the MM5 session. From MM6 on it is the default link layer, so a bug
in a student's own MM5 code cannot block the MM6 lab.
"""
from ..frames import ACK, DATA, Frame
from ..node import LinkProtocol


class StopAndWaitSender(LinkProtocol):
    def on_start(self, ctx):
        self.seq = 0
        self.current = None
        self._send_next(ctx)

    def on_data_ready(self, ctx):
        if self.current is None:
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
        if frame.ack == (self.seq + 1) % 2:      # Bob now expects the next frame
            ctx.cancel_timer("retransmit")
            self.seq = (self.seq + 1) % 2
            self._send_next(ctx)

    def on_timer(self, ctx, name):
        if self.current is not None:
            self._transmit(ctx)


class StopAndWaitReceiver(LinkProtocol):
    def on_start(self, ctx):
        self.expected = 0

    def on_frame(self, ctx, frame):
        if not frame.check_ok or frame.kind != DATA:
            return                                # stay silent: implicit NACK
        if frame.seq == self.expected:
            ctx.deliver(frame.payload)
            self.expected = (self.expected + 1) % 2
        ctx.send(Frame(kind=ACK, ack=self.expected))  # duplicates are re-ACKed, not delivered
