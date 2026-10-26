"""MM7 - your helpers for the layering lab.

This is the only file you change in the MM7 lab (together with the lab notebook).
The layer engine in commsim/ is given: here you only write two small functions, one
for each part of the lab. Use Copilot if you like, but read what it writes.

STATUS IN THIS EXAMPLE: solved. This is what a group's file could look like at the
end of the MM7 session. What students were handed at the start is kept in
instructor/starters/mm7_layers.py.
"""


# =============================================================================
# Part A4: packet size after each layer
# =============================================================================

def packet_sizes(payload_bytes, header_sizes):
    """Size of the packet after each layer on the way down Zoya's stack.

    payload_bytes   size of the application data, in bytes
    header_sizes    header size in bytes of each layer that adds one, from the top down,
                    e.g. [8, 12, 10] for transport, network, data link

    Specification
      1. Return a list with len(header_sizes) + 1 numbers.
      2. The first number is the payload on its own.
      3. Each next number is the packet after one more layer has put its header in
         front of everything it got from the layer above.
      4. Do not change header_sizes.

    Then run check_mm7_encapsulation(packet_sizes) in the notebook.
    """
    sizes = [payload_bytes]                 # before any layer has added a header
    for header in header_sizes:
        sizes.append(sizes[-1] + header)    # this layer wraps everything from above
    return sizes


# =============================================================================
# Part B: when to retransmit, and when to give up
# =============================================================================

def retry_decision(waited, retransmissions, timeout, max_retransmissions):
    """What to do with a packet that has been sent but not acknowledged yet.

    Both the lower layer (LL) and the higher layer (HL) use this rule, each with its own
    timeout and retry limit. While a layer waits for an ACK, the framework calls this
    function once per slot. When the ACK arrives, it stops asking.

    waited               slots since the packet was last sent (or resent)
    retransmissions      how many times it has been retransmitted so far (0 after the first send)
    timeout              T: slots to wait for the ACK before doing anything
    max_retransmissions  K: retransmit at most this many times, then give up

    Specification
      1. Retry only after the timeout: as long as waited < timeout, return "wait".
      2. When the timeout has expired and retransmissions < max_retransmissions,
         return "retransmit".
      3. When the timeout has expired and the packet has already been retransmitted
         max_retransmissions times, return "give_up".

    Then run check_mm7_retry(retry_decision) in the notebook.
    """
    if waited < timeout:
        return "wait"                       # the ACK may still be on its way
    if retransmissions < max_retransmissions:
        return "retransmit"
    return "give_up"                        # K retransmissions used up: report failure
