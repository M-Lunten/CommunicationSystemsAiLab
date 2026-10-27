"""MM9 - your security functions.

This is the only file you change in the MM9 lab (together with the lab notebook).
The block cipher, Diffie-Hellman and the chat simulator in commsim/ are given: here you
write four small functions. Use Copilot if you like, but read what it writes.
"""
import hashlib
import hmac

from commsim.crypto import toy_decrypt_block, toy_encrypt_block, xor_bytes


# =============================================================================
# Question 1: Cipher Block Chaining (Lecture 9)
# =============================================================================
#
# Given, in commsim.crypto:
#   toy_encrypt_block(block, key)   encrypt one 8-byte block (a toy cipher, NOT secure)
#   toy_decrypt_block(block, key)   undo it
#   xor_bytes(a, b)                 bytewise XOR of two 8-byte blocks
#   ecb_encrypt(blocks, key)        ECB, as an example: every block encrypted on its own

def cbc_encrypt(blocks, key, iv):
    """Encrypt a list of 8-byte plaintext blocks with Cipher Block Chaining.

    Specification
      1. C[0] = E(P[0] XOR iv)
      2. C[i] = E(P[i] XOR C[i-1]) for every next block
         where E is toy_encrypt_block with `key`.
      3. Return the list of ciphertext blocks (same length as `blocks`).
      4. Do not change `blocks`.
    """
    raise NotImplementedError("Question 1: implement cbc_encrypt")


def cbc_decrypt(blocks, key, iv):
    """Decrypt a list of 8-byte ciphertext blocks made by cbc_encrypt.

    Specification
      1. P[0] = D(C[0]) XOR iv
      2. P[i] = D(C[i]) XOR C[i-1]
         where D is toy_decrypt_block with `key`.
      3. Return the list of plaintext blocks. Never raise an error because a block looks
         wrong: decryption cannot tell.

    Then run check_mm9_cbc(cbc_encrypt, cbc_decrypt) in the notebook.
    """
    raise NotImplementedError("Question 1: implement cbc_decrypt")


# =============================================================================
# Question 2: authenticating Diffie-Hellman with a pre-shared key (Problem Set 5, Problem 4)
# =============================================================================

def respond(K, challenge, public_value):
    """Answer the other side's challenge, binding the answer to your own public value.

    K              the pre-shared key (bytes)
    challenge      the random challenge the other side sent (bytes)
    public_value   YOUR OWN Diffie-Hellman public value (an int)

    Specification: return the SHA-256 hash, as a hex string, of
        K + challenge + str(public_value).encode()
    i.e. hashlib.sha256(...).hexdigest(). Only someone who knows K can compute it.
    """
    raise NotImplementedError("Question 2: implement respond")


def verify(K, challenge, public_value, response):
    """Check the other side's answer to YOUR challenge.

    public_value   the other side's public value, as YOU received it
    response       what the other side sent back

    Specification: True if `response` equals respond(K, challenge, public_value), else
    False. Compare with hmac.compare_digest. Then run check_mm9_auth(respond, verify).
    """
    raise NotImplementedError("Question 2: implement verify")
