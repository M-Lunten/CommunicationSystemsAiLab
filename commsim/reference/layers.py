"""Reference solutions for the MM7 lab (Lecture 7).

Released after the MM7 session, so later labs (and groups that did not finish) have a
working packet-size helper and retry rule.
"""


def packet_sizes(payload_bytes, header_sizes):
    """Payload size, then the packet size after each layer adds its header."""
    sizes = [payload_bytes]
    for header in header_sizes:
        sizes.append(sizes[-1] + header)
    return sizes


def retry_decision(waited, retransmissions, timeout, max_retransmissions):
    """Wait until the timeout, then retransmit up to the limit, then give up."""
    if waited < timeout:
        return "wait"
    if retransmissions < max_retransmissions:
        return "retransmit"
    return "give_up"
