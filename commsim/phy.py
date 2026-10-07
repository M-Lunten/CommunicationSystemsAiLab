"""Physical layer: turns transmitted bits into received bits.

MM5-MM9 use the Binary Symmetric Channel from Lecture 5: every bit is flipped
independently with probability `ber`.

Growth path (MM10-MM11): a modulation layer (e.g. BPSK/QPSK over a noisy channel)
replaces this class. It only needs the same `corrupt(bits) -> bits` method, so
nothing above the physical layer has to change.
"""
import numpy as np


class BinarySymmetricChannel:
    def __init__(self, ber=0.0, rng=None):
        self.ber = float(ber)
        self.rng = rng if rng is not None else np.random.default_rng()

    def corrupt(self, bits):
        if self.ber <= 0.0:
            return bits.copy()
        flips = (self.rng.random(bits.size) < self.ber).astype(np.uint8)
        return bits ^ flips

    def __repr__(self):
        return f"BinarySymmetricChannel(ber={self.ber:g})"
