"""Block ciphers and their modes (MM9, Question 1).

TOY CIPHER, NOT SECURE. toy_encrypt_block is a 4-round Feistel network on 8-byte blocks.
It behaves enough like a real block cipher (AES, DES) for this lab: the same block and key
always give the same output, and one changed input bit scrambles the whole output block.
Never use it to protect real data.

Given here:  toy_encrypt_block, toy_decrypt_block, xor_bytes, ecb_encrypt, ecb_decrypt,
             and the lab scenarios (sensor log, bit flips, lost blocks, Eve's attack).
Students:    cbc_encrypt and cbc_decrypt in student/mm9_security.py.
"""
import zlib

BLOCK = 8
DEMO_KEY = b"MM9-demo-key-16B"
DEMO_IV = bytes.fromhex("3a91c4077be25d18")
_MASK = 0xFFFFFFFF


# ---------------------------------------------------------------- the toy block cipher

def _round_keys(key):
    if not key:
        raise ValueError("the key must not be empty")
    state = zlib.crc32(key)
    keys = []
    for i in range(4):
        state = (state * 0x9E3779B1 + 0x7F4A7C15 + i + zlib.crc32(key, i)) & _MASK
        keys.append(state)
    return keys


def _f(half, k):
    x = (half ^ k) & _MASK
    x = (x * 0x85EBCA6B) & _MASK
    x ^= x >> 13
    x = (x * 0xC2B2AE35) & _MASK
    return x ^ (x >> 16)


def _check_block(block):
    if not isinstance(block, (bytes, bytearray)) or len(block) != BLOCK:
        raise ValueError(f"a block must be {BLOCK} bytes, got {block!r}")


def toy_encrypt_block(block, key):
    """Encrypt one 8-byte block with `key` (bytes). Returns 8 bytes."""
    _check_block(block)
    left, right = int.from_bytes(block[:4], "big"), int.from_bytes(block[4:], "big")
    for k in _round_keys(key):
        left, right = right, left ^ _f(right, k)
    return left.to_bytes(4, "big") + right.to_bytes(4, "big")


def toy_decrypt_block(block, key):
    """Undo toy_encrypt_block. Returns 8 bytes."""
    _check_block(block)
    left, right = int.from_bytes(block[:4], "big"), int.from_bytes(block[4:], "big")
    for k in reversed(_round_keys(key)):
        left, right = right ^ _f(left, k), left
    return left.to_bytes(4, "big") + right.to_bytes(4, "big")


def xor_bytes(a, b):
    """Bytewise XOR of two equally long byte strings."""
    if len(a) != len(b):
        raise ValueError("xor_bytes needs two byte strings of the same length")
    return bytes(x ^ y for x, y in zip(a, b))


# ---------------------------------------------------------------- ECB (given)

def ecb_encrypt(blocks, key):
    """Electronic Code Book: every block is encrypted on its own."""
    return [toy_encrypt_block(b, key) for b in blocks]


def ecb_decrypt(blocks, key):
    return [toy_decrypt_block(b, key) for b in blocks]


# ---------------------------------------------------------------- lab scenarios

READINGS = {"normal": b"T=21.5C ", "warm": b"T=23.0C ", "alarm": b"T=58.0C "}


def sensor_log():
    """64 temperature readings of 8 bytes, with only 3 different values: mostly normal,
    the heating makes it warm for a while, and once there is an alarm."""
    log = []
    for i in range(64):
        if i == 45:
            log.append(READINGS["alarm"])
        elif 20 <= i < 36:
            log.append(READINGS["warm"])
        else:
            log.append(READINGS["normal"])
    return log


def to_blocks(data):
    """Split bytes into 8-byte blocks, padding the last one with spaces."""
    data = bytes(data)
    if len(data) % BLOCK:
        data += b" " * (BLOCK - len(data) % BLOCK)
    return [data[i:i + BLOCK] for i in range(0, len(data), BLOCK)]


def flip_bit(blocks, block, bit=0):
    """A copy of `blocks` with one bit flipped in block number `block` (a transmission error)."""
    out = list(blocks)
    b = bytearray(out[block])
    b[bit // 8] ^= 0x80 >> (bit % 8)
    out[block] = bytes(b)
    return out


def drop_block(blocks, block):
    """A copy of `blocks` with block number `block` removed (a lost packet)."""
    return blocks[:block] + blocks[block + 1:]


def damaged_blocks(original, received, lost=None):
    """Indices of the original plaintext blocks that the receiver did not get right.
    If block `lost` was lost on the way, it counts as damaged, and the received blocks
    after it are compared with the original blocks after it."""
    received = list(received)
    if lost is not None:
        received = received[:lost] + [None] + received[lost:]
    return [i for i, b in enumerate(original) if i >= len(received) or received[i] != b]


def meter_message(reading="0100"):
    """Zoya's smart meter sends one 8-byte block: 4 ASCII digits and a CRC-32 of them."""
    digits = reading.encode()
    if len(digits) != 4:
        raise ValueError("the reading must have 4 digits")
    return [digits + zlib.crc32(digits).to_bytes(4, "big")]


def read_meter(blocks):
    """What Yoshi's side reads from a decrypted meter message: (reading, crc_ok)."""
    block = blocks[0]
    digits, crc = block[:4], block[4:]
    return digits.decode(errors="replace"), zlib.crc32(digits).to_bytes(4, "big") == crc


def eve_change(iv, ciphertext, old="0100", new="0900", fix_crc=True):
    """Eve's bit-flipping attack on CBC, without the key.

    The IV travels in the clear. Because the first plaintext block is D(C1) XOR IV, flipping
    bits in the IV flips exactly the same bits in the decrypted first block. Eve guesses the
    reading `old` and wants Yoshi to read `new`. With fix_crc=True she also changes the CRC
    bytes: the CRC uses no key, so she can compute both CRCs herself.
    Returns (iv, ciphertext) as Eve forwards them."""
    delta = xor_bytes(old.encode(), new.encode())
    if fix_crc:
        delta += xor_bytes(zlib.crc32(old.encode()).to_bytes(4, "big"),
                           zlib.crc32(new.encode()).to_bytes(4, "big"))
    else:
        delta += bytes(4)
    return xor_bytes(iv, delta), list(ciphertext)
