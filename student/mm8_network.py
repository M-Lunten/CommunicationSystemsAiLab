"""MM8 - your routing and flow-control rules.

This is the only file you change in the MM8 lab (together with the lab notebook).
The routing and flow-control engines in commsim/ are given: here you write three small
functions. Use Copilot if you like, but read what it writes.
"""


# =============================================================================
# Question 1: distance-vector routing (Bellman-Ford, Lecture 8)
# =============================================================================

def dv_update(me, link_costs, neighbour_vectors):
    """Compute one router's new routing table from what its neighbours told it.

    me                  this router's name, e.g. "C"
    link_costs          cost of the link to each neighbour, e.g. {"B": 6, "D": 3, "E": 5}
    neighbour_vectors   each neighbour's distance vector, e.g.
                        {"B": {"A": 5, "B": 0, "C": 8, ...}, "D": {...}, ...}

    Specification
      1. Return (distances, next_hops): two dicts keyed by destination.
      2. Include every destination that appears in any neighbour's vector, and `me`.
      3. The distance to `me` is 0 and its next hop is None.
      4. For every other destination d: distances[d] is the smallest
         link_costs[n] + neighbour_vectors[n][d] over the neighbours n that know d,
         and next_hops[d] is that neighbour.
      5. On a tie, keep the neighbour that comes first in link_costs.
      6. Do not change link_costs or neighbour_vectors.

    (The engine handles "infinity": any distance of 16 or more means unreachable.)
    Then run check_mm8_dv(dv_update) in the notebook.
    """
    raise NotImplementedError("Question 1: implement dv_update")


# =============================================================================
# Question 2: flow control (Lecture 8)
# =============================================================================

def advertised_window(buffer_size, queued):
    """Receiver side: how many more packets the sender may have on the way.

    buffer_size   receiver buffer in packets (including the packet being processed)
    queued        packets in the buffer right now

    Specification: return the free space in the buffer (never less than 0).
    """
    raise NotImplementedError("Question 2: implement advertised_window")


def may_send(in_flight, window):
    """Sender side: may the sender put one more packet on the link now?

    in_flight   packets sent that the receiver has not yet reported as arrived
    window      the receiver's last advertised window

    Specification: True while fewer than `window` packets are in flight, otherwise False.
    Then run check_mm8_flow(advertised_window, may_send) in the notebook.
    """
    raise NotImplementedError("Question 2: implement may_send")
