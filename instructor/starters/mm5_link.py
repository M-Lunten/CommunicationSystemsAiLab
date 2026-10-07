"""MM5 - your link layer.

This is the only file you change in the MM5 lab (together with the lab notebook).
The rest of the framework (commsim/) is fixed.

Your protocol talks to the rest of the system only through `ctx`:

    ctx.next_payload()           next bytes from the application, or None
    ctx.send(Frame(...))         transmit a frame to the other side
    ctx.start_timer(name, sec)   on_timer(ctx, name) is called after `sec` seconds
    ctx.cancel_timer(name)       stop a timer
    ctx.deliver(payload)         hand data to Bob's application
    ctx.params["timeout"]        a suitable retransmission timeout for this scenario

Frames: Frame(kind=DATA, seq=..., payload=...) or Frame(kind=ACK, ack=...).
A received frame has frame.check_ok == False if its error check failed.
"""
from commsim import ACK, DATA, Frame, LinkProtocol


# =============================================================================
# Given example: "Utopia". Send everything at once, trust everything you receive.
# Read it to see how the methods and ctx are used.
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
# Part B: implement stop-and-wait ARQ (Lecture 5). Use Copilot if you like.
#
# Specification
#   Sender
#     1. Send one DATA frame at a time, then wait.
#     2. Start a timer when you send it (duration ctx.params["timeout"]).
#     3. When the ACK for that frame arrives: stop the timer and send the next payload.
#     4. When the timer expires: send the same frame again.
#     5. When idle and the application gets new data (on_data_ready): start sending.
#   Receiver
#     6. Ignore frames whose error check failed (frame.check_ok is False).
#     7. Deliver each payload to the application exactly once, in order.
#     8. Answer every intact DATA frame with an ACK.
#   Both
#     9. Use a 1-bit sequence number so Bob can recognise a retransmitted copy.
#        Convention: the ACK carries the sequence bit Bob expects NEXT.
#
# Then run check_mm5(StopAndWaitSender, StopAndWaitReceiver) in the notebook.
# =============================================================================

class StopAndWaitSender(LinkProtocol):
    def on_start(self, ctx):
        raise NotImplementedError("Part B: implement the sender")

    def on_data_ready(self, ctx):
        raise NotImplementedError

    def on_frame(self, ctx, frame):
        raise NotImplementedError

    def on_timer(self, ctx, name):
        raise NotImplementedError


class StopAndWaitReceiver(LinkProtocol):
    def on_start(self, ctx):
        raise NotImplementedError("Part B: implement the receiver")

    def on_frame(self, ctx, frame):
        raise NotImplementedError
