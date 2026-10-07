"""Frames, the frame format, and error detection.

A protocol builds a `Frame` object; the framework turns it into real bits
(preamble, header fields, payload, check bits), sends the bits through the
channel, and parses whatever arrives. Bit errors can therefore hit any field,
including the length field and the check bits, just like in Lecture 5.
"""
import binascii
import math
import zlib
from dataclasses import dataclass, field

import numpy as np

DATA = "DATA"
ACK = "ACK"


@dataclass
class Frame:
    """What a protocol sends and receives.

    kind     'DATA' or 'ACK'
    seq      sequence number of this data frame
    ack      acknowledgement number (which sequence number the receiver expects next)
    payload  bytes from the application (DATA frames only)

    Filled in by the framework (don't set them yourself):
    src, dst  addresses of sender and receiver
    check_ok  False if the receiver's error check failed. The header fields of a
              frame with check_ok == False cannot be trusted.
    """
    kind: str = DATA
    seq: int = 0
    ack: int = 0
    payload: bytes = b""
    src: int = 0
    dst: int = 0
    check_ok: bool = True
    nbits: int = field(default=0, compare=False)


# ---------------------------------------------------------------- error detection

def _crc8(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc = _CRC8_TABLE[crc ^ byte]
    return crc


def _make_crc8_table(poly=0x07):
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = ((c << 1) ^ poly) & 0xFF if c & 0x80 else (c << 1) & 0xFF
        table.append(c)
    return table


_CRC8_TABLE = _make_crc8_table()

CHECKS = {
    # name: (number of check bits, function from covered bits to an int)
    "none": (0, None),
    "parity": (1, lambda bits: int(bits.sum()) & 1),            # even parity
    "crc8": (8, lambda bits: _crc8(np.packbits(bits).tobytes())),
    "crc16": (16, lambda bits: binascii.crc_hqx(np.packbits(bits).tobytes(), 0xFFFF)),
    "crc32": (32, lambda bits: zlib.crc32(np.packbits(bits).tobytes())),
}


def _int_to_bits(value, n):
    if n == 0:
        return np.zeros(0, dtype=np.uint8)
    return ((int(value) >> np.arange(n - 1, -1, -1)) & 1).astype(np.uint8)


def _bits_to_int(bits):
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return value


# ---------------------------------------------------------------- frame format

class FrameFormat:
    """Layout of a frame on the wire.

    | preamble | dst | src | type | seq | ack | length | payload | check |

    ACK frames have no length field and no payload.
    The length field is just wide enough for payloads of 1..max_payload_bytes
    bytes ("fixing the maximum length fixes the number of length bits", Lecture 5).
    """

    PREAMBLE_PATTERN = 0b10101010

    def __init__(self, max_payload_bytes=64, check="crc8", addr_bits=0, seq_bits=1,
                 preamble_bits=8):
        if check not in CHECKS:
            raise ValueError(f"check must be one of {list(CHECKS)}")
        self.max_payload_bytes = int(max_payload_bytes)
        self.check = check
        self.addr_bits = int(addr_bits)
        self.seq_bits = int(seq_bits)
        self.preamble_bits = int(preamble_bits)
        self.length_bits = max(1, math.ceil(math.log2(self.max_payload_bytes)))
        self.check_bits = CHECKS[check][0]
        pattern = np.array([(i + 1) % 2 for i in range(self.preamble_bits)], dtype=np.uint8)
        self.preamble = pattern  # 1010...

    # sizes -------------------------------------------------------------
    @property
    def ack_header_bits(self):
        return (self.preamble_bits + 2 * self.addr_bits + 1 + 2 * self.seq_bits)

    @property
    def data_overhead_bits(self):
        """Control bits in a DATA frame (everything except the payload)."""
        return self.ack_header_bits + self.length_bits + self.check_bits

    @property
    def ack_bits(self):
        return self.ack_header_bits + self.check_bits

    def data_bits(self, payload_bytes):
        return self.data_overhead_bits + 8 * payload_bytes

    def describe(self):
        rows = [("preamble", self.preamble_bits), ("dst address", self.addr_bits),
                ("src address", self.addr_bits), ("type (DATA/ACK)", 1),
                ("seq", self.seq_bits), ("ack", self.seq_bits),
                ("length", self.length_bits),
                ("payload", f"8 x (1..{self.max_payload_bytes})"),
                (f"check ({self.check})", self.check_bits)]
        lines = [f"{name:<18}{bits}" for name, bits in rows]
        lines.append(f"{'= overhead':<18}{self.data_overhead_bits} bits per DATA frame, "
                     f"ACK frame = {self.ack_bits} bits")
        return "\n".join(lines)

    # encode / decode ---------------------------------------------------
    def encode(self, frame: Frame) -> np.ndarray:
        is_data = frame.kind == DATA
        mod = 1 << self.seq_bits
        parts = [
            _int_to_bits(frame.dst, self.addr_bits),
            _int_to_bits(frame.src, self.addr_bits),
            _int_to_bits(0 if is_data else 1, 1),
            _int_to_bits(frame.seq % mod, self.seq_bits),
            _int_to_bits(frame.ack % mod, self.seq_bits),
        ]
        if is_data:
            n = len(frame.payload)
            if not 1 <= n <= self.max_payload_bytes:
                raise ValueError(f"payload must be 1..{self.max_payload_bytes} bytes, got {n}")
            parts.append(_int_to_bits(n - 1, self.length_bits))
            parts.append(np.unpackbits(np.frombuffer(frame.payload, dtype=np.uint8)))
        covered = np.concatenate(parts)
        bits_n, fn = CHECKS[self.check]
        check = _int_to_bits(fn(covered), bits_n) if fn else np.zeros(0, dtype=np.uint8)
        return np.concatenate([self.preamble, covered, check])

    def decode(self, bits: np.ndarray):
        """Return the received Frame, or None if the preamble was not recognised."""
        p = self.preamble_bits
        if bits.size < p or not np.array_equal(bits[:p], self.preamble):
            return None
        pos = p
        a, s = self.addr_bits, self.seq_bits

        def take(n):
            nonlocal pos
            chunk = bits[pos:pos + n]
            pos += n
            return chunk

        dst = _bits_to_int(take(a))
        src = _bits_to_int(take(a))
        is_data = _bits_to_int(take(1)) == 0
        seq = _bits_to_int(take(s))
        ack = _bits_to_int(take(s))
        payload = b""
        if is_data:
            n = _bits_to_int(take(self.length_bits)) + 1
            payload_bits = take(8 * n)
            if payload_bits.size % 8:
                payload_bits = np.concatenate(
                    [payload_bits, np.zeros(8 - payload_bits.size % 8, dtype=np.uint8)])
            payload = np.packbits(payload_bits).tobytes()
        covered_end = pos
        bits_n, fn = CHECKS[self.check]
        received_check = bits[pos:pos + bits_n]
        expected_len = pos + bits_n
        if fn is None:
            ok = True  # no error detection: the receiver has no way to notice errors
        else:
            # Like a real receiver, trust the (possibly corrupted) length field and
            # compare the check bits found where the length field says they are.
            ok = (bits.size >= expected_len and
                  _bits_to_int(received_check) == fn(bits[p:covered_end]))
        return Frame(kind=DATA if is_data else ACK, seq=seq, ack=ack, payload=payload,
                     src=src, dst=dst, check_ok=bool(ok), nbits=int(bits.size))
