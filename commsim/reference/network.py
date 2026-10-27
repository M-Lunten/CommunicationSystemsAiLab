"""Reference solutions for the MM8 lab (Lecture 8).

Released after the MM8 session: one distance-vector (Bellman-Ford) update, and the two
flow-control rules.
"""


def dv_update(me, link_costs, neighbour_vectors):
    """New (distances, next_hops) for router `me` from its neighbours' vectors."""
    destinations = {me} | {d for vector in neighbour_vectors.values() for d in vector}
    distances, next_hops = {}, {}
    for d in destinations:
        if d == me:
            distances[d], next_hops[d] = 0, None
            continue
        for n, cost in link_costs.items():          # first neighbour wins a tie
            if d in neighbour_vectors.get(n, {}):
                total = cost + neighbour_vectors[n][d]
                if d not in distances or total < distances[d]:
                    distances[d], next_hops[d] = total, n
    return distances, next_hops


def advertised_window(buffer_size, queued):
    """Free space in the receiver buffer."""
    return max(0, buffer_size - queued)


def may_send(in_flight, window):
    """The sender may send while fewer than `window` packets are in flight."""
    return in_flight < window
