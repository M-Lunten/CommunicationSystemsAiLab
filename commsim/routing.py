"""Distance-vector routing (MM8, Question 1).

Every router keeps a distance vector: its best known distance, and the next hop, to every
destination. In each round, all routers send their vectors to their neighbours at the same
time, and then every router computes its new table with the student's dv_update. This is
the Bellman-Ford update of Lecture 8.

Conventions (as in RIP):
* rounds are synchronous: everyone uses the vectors from the end of the previous round;
* a distance of `infinity` (16) or more means "unreachable";
* only rounds in which some table entry changed are counted.

With poisoned reverse, a router tells a neighbour "infinity" for every destination it
reaches *through* that neighbour.
"""
from dataclasses import dataclass, field

INFINITY = 16

CHAIN = ["Zoya", "R1", "R2", "R3", "Yoshi"]

# Problem Set 4, Problem 2: what router C receives
PS4_PROBLEM2 = {
    "link_costs": {"B": 6, "D": 3, "E": 5},
    "neighbour_vectors": {
        "B": dict(zip("ABCDEF", (5, 0, 8, 12, 6, 2))),
        "D": dict(zip("ABCDEF", (16, 12, 6, 0, 9, 10))),
        "E": dict(zip("ABCDEF", (7, 6, 3, 9, 0, 4))),
    },
}


@dataclass
class RoutingResults:
    scenario: str
    nodes: list
    destination: str
    rounds_to_start: int            # rounds until the tables first stopped changing
    rounds_after_failure: int       # rounds with a change after the link failed (0 if none failed)
    history: list = field(default_factory=list, repr=False)   # tables after each round after the failure
    before: dict = field(default_factory=dict, repr=False)    # tables just before the failure
    infinity: int = INFINITY

    def _cell(self, tables, node):
        dist, hop = tables[node]
        d = dist.get(self.destination, self.infinity)
        if d >= self.infinity:
            return "inf"
        return f"{d} via {hop[self.destination]}" if hop.get(self.destination) else f"{d}"

    def summary(self):
        lines = [self.scenario,
                 f"  rounds to build the tables at the start   {self.rounds_to_start}",
                 f"  rounds with a change after the failure    {self.rounds_after_failure}",
                 "", f"  distance to {self.destination} (and next hop) at each router"]
        width = 14
        cols = [n for n in self.nodes if n != self.destination]
        lines.append("  " + f"{'round':<7}" + "".join(f"{n:>{width}}" for n in cols))
        lines.append("  " + f"{'before':<7}" + "".join(f"{self._cell(self.before, n):>{width}}"
                                                       for n in cols))
        for i, tables in enumerate(self.history, start=1):
            lines.append("  " + f"{i:<7}" + "".join(f"{self._cell(tables, n):>{width}}"
                                                     for n in cols))
        return "\n".join(lines)

    def distances(self, node):
        """Distance from `node` to the destination before the failure and after each round."""
        return [min(t[node][0].get(self.destination, self.infinity), self.infinity)
                for t in [self.before] + self.history]

    def __str__(self):
        return self.summary()

    def _repr_pretty_(self, p, cycle):
        p.text(self.summary())


def _check_output(out, me):
    if not (isinstance(out, tuple) and len(out) == 2 and all(isinstance(x, dict) for x in out)):
        raise TypeError(f"dv_update must return (distances, next_hops), two dicts; for {me} it "
                        f"returned {out!r}")
    return out


def distance_vector(dv_update, links, *, fail=None, destination=None, infinity=INFINITY,
                    poisoned_reverse=False, max_rounds=200):
    """Run distance-vector routing on a network until the tables stop changing, then
    (optionally) fail one link and run again.

    dv_update          your dv_update(me, link_costs, neighbour_vectors)
    links              {(node, node): cost}
    fail               the link to cut after the tables have settled, e.g. ("R3", "Yoshi")
    destination        whose column to show (default: the second node of `fail`)
    infinity           a distance this large or larger means unreachable
    poisoned_reverse   advertise infinity back to the neighbour a route goes through
    """
    links = {tuple(k): v for k, v in links.items()}
    nodes = list(dict.fromkeys(n for link in links for n in link))
    tables = {n: ({n: 0}, {n: None}) for n in nodes}

    def neighbours(n):
        return {(b if a == n else a): c for (a, b), c in links.items() if n in (a, b)}

    def advertised(m, to):
        dist, hop = tables[m]
        return {d: (infinity if poisoned_reverse and hop.get(d) == to else min(v, infinity))
                for d, v in dist.items()}

    def one_round():
        new = {}
        for n in nodes:
            costs = neighbours(n)
            vectors = {m: advertised(m, n) for m in costs}
            dist, hop = _check_output(dv_update(n, dict(costs), vectors), n)
            dests = set(dist) | {d for v in vectors.values() for d in v} | set(tables[n][0])
            clean_d, clean_h = {}, {}
            for d in dests:
                v = dist.get(d, infinity)
                v = infinity if v is None else min(v, infinity)
                clean_d[d] = 0 if d == n else v
                clean_h[d] = None if (d == n or v >= infinity) else hop.get(d)
            new[n] = (clean_d, clean_h)
        return new

    def run(history):
        nonlocal tables
        for _ in range(max_rounds):
            new = one_round()
            if new == tables:
                return
            tables = new
            if history is not None:
                history.append({n: (dict(d), dict(h)) for n, (d, h) in tables.items()})
        raise RuntimeError(f"no convergence after {max_rounds} rounds")

    start = []
    run(start)
    before = {n: (dict(d), dict(h)) for n, (d, h) in tables.items()}
    history = []
    if fail is not None:
        if tuple(fail) not in links and tuple(fail[::-1]) not in links:
            raise ValueError(f"there is no link {fail}")
        links.pop(tuple(fail), None)
        links.pop(tuple(fail[::-1]), None)
        run(history)
    dest = destination or (fail[1] if fail else nodes[-1])
    label = (f"distance_vector: {len(nodes)} routers"
             + (f", link {fail[0]}-{fail[1]} fails" if fail else "")
             + f", infinity = {infinity}" + (", poisoned reverse" if poisoned_reverse else ""))
    return RoutingResults(label, nodes, dest, len(start), len(history), history, before, infinity)


def chain_routing(dv_update, *, fail=("R3", "Yoshi"), poisoned_reverse=False, infinity=INFINITY):
    """The chain Zoya - R1 - R2 - R3 - Yoshi, every link costs 1. By default the R3-Yoshi
    link fails once the tables have settled."""
    links = {(a, b): 1 for a, b in zip(CHAIN, CHAIN[1:])}
    return distance_vector(dv_update, links, fail=fail, infinity=infinity,
                           poisoned_reverse=poisoned_reverse)
