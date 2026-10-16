"""Layered protocol stacks (MM7, Part A): follow one packet from Zoya to Yoshi via a router.

Zoya and Yoshi run the full 7-layer OSI stack. The router between them only has
layers 1-3: it takes the frame off the first link, reads the network header to decide
where the packet goes, and puts it in a new frame for the second link.

    Zoya (L7..L1)  --link 1-->  Router (L1..L3)  --link 2-->  Yoshi (L1..L7)

Every layer with a header size > 0 adds its header on the way down and removes it on
the way up. The trace records what happens at each node and layer, the packet size
after every step, and the header fields on each link.
"""
from dataclasses import dataclass, field

LAYERS = {7: "application", 6: "presentation", 5: "session", 4: "transport", 3: "network",
          2: "data link", 1: "physical"}
SHORT = {7: "APP", 6: "PRES", 5: "SESS", 4: "TRANS", 3: "NET", 2: "DL", 1: "PHY"}
ROUTER_LAYERS = 3


@dataclass
class Header:
    layer: int
    size: int
    fields: dict

    @property
    def name(self):
        return LAYERS[self.layer]


@dataclass
class Step:
    node: str
    layer: int
    action: str          # "add", "remove", "pass", "process", "send", "receive"
    note: str
    size: int            # packet size in bytes after this step
    delta: int = 0       # bytes added (+) or removed (-) in this step


@dataclass
class LayerTrace:
    payload_bytes: int
    header_sizes: dict                     # layer number -> bytes (link 1)
    steps: list = field(default_factory=list)
    links: dict = field(default_factory=dict)   # "link 1"/"link 2" -> list of Headers, outermost first
    highest_layer: dict = field(default_factory=dict)

    @property
    def packet_bytes(self):
        """Size of the packet on the first link (payload plus all headers)."""
        return self.payload_bytes + sum(h.size for h in self.links["link 1"])

    @property
    def efficiency(self):
        """Fraction of the bytes on the first link that are application data."""
        return self.payload_bytes / self.packet_bytes

    def link_bytes(self, link):
        return self.payload_bytes + sum(h.size for h in self.links[link])

    def summary(self):
        hdrs = ", ".join(f"{LAYERS[n]} {s} B" for n, s in sorted(self.header_sizes.items(),
                                                                    reverse=True) if s)
        lines = [f"Zoya -> Router -> Yoshi: {self.payload_bytes} B of application data",
                 f"  headers              {hdrs or 'none'}",
                 f"  packet on link 1     {self.link_bytes('link 1')} B",
                 f"  packet on link 2     {self.link_bytes('link 2')} B",
                 f"  payload efficiency   {self.efficiency:.3f}  "
                 f"({self.payload_bytes} of {self.packet_bytes} B are application data)",
                 "  highest layer        " + ", ".join(f"{n}: L{l}" for n, l in self.highest_layer.items()),
                 "", "  step by step"]
        for s in self.steps:
            lines.append(f"    {s.node:<7}L{s.layer} {LAYERS[s.layer]:<13}{s.note:<44}{s.size:>5} B")
        lines += ["", f"  header fields{'':<22}{'link 1':<22}link 2"]
        l1 = {(h.layer, k): v for h in self.links["link 1"] for k, v in h.fields.items()}
        l2 = {(h.layer, k): v for h in self.links["link 2"] for k, v in h.fields.items()}
        for key in l1:
            mark = "   <- changed" if l1[key] != l2.get(key) else ""
            name = f"L{key[0]} {key[1]}"
            lines.append(f"    {name:<31}{str(l1[key]):<22}{str(l2.get(key, '-')):<16}{mark}")
        return "\n".join(lines)

    def __str__(self):
        return self.summary()

    def _repr_pretty_(self, p, cycle):
        p.text(self.summary())


def _fields(layer, hop):
    """Example header contents. Only the data link header depends on the hop."""
    if layer == 2:
        return ({"src": "zoya-eth0", "dst": "router-eth0"} if hop == 1
                else {"src": "router-eth1", "dst": "yoshi-eth0"})
    if layer == 3:
        return {"src": "10.0.1.7 (Zoya)", "dst": "10.0.2.9 (Yoshi)", "TTL": 64 if hop == 1 else 63}
    if layer == 4:
        return {"src port": 50000, "dst port": 80}
    if layer == 5:
        return {"session id": 17}
    if layer == 6:
        return {"encoding": "UTF-8"}
    if layer == 7:
        return {"app": "chat"}
    return {}


def zoya_router_yoshi(payload_bytes=100, *, application=0, presentation=0, session=0,
                      transport=8, network=12, data_link=10, data_link_out=None):
    """Zoya sends one packet to Yoshi through a router (Problem Set 7, Problem 1(c)).

    payload_bytes   application data in bytes
    application, presentation, session, transport, network, data_link
                    header size in bytes added by each layer (0 = no header)
    data_link_out   data link header size on the router's outgoing link
                    (default: the same as data_link)

    Returns a LayerTrace: print it, or draw it with layer_diagram(trace).
    """
    sizes = {7: application, 6: presentation, 5: session, 4: transport, 3: network, 2: data_link, 1: 0}
    for layer, s in sizes.items():
        if s < 0:
            raise ValueError(f"{LAYERS[layer]} header size must be >= 0")
    out_sizes = {**sizes, 2: data_link if data_link_out is None else data_link_out}
    trace = LayerTrace(payload_bytes, {k: v for k, v in sizes.items() if k > 1})

    # Zoya: down the stack
    stack, size = [], payload_bytes
    for layer in range(7, 0, -1):
        if layer == 1:
            trace.steps.append(Step("Zoya", 1, "send", "send the bits on link 1", size))
        elif sizes[layer]:
            stack.insert(0, Header(layer, sizes[layer], _fields(layer, 1)))
            size += sizes[layer]
            trace.steps.append(Step("Zoya", layer, "add", f"add {sizes[layer]} B header", size,
                                   sizes[layer]))
        else:
            trace.steps.append(Step("Zoya", layer, "pass", "pass down (no header)", size))
    trace.links["link 1"] = [Header(h.layer, h.size, dict(h.fields)) for h in stack]

    # Router: up to layer 3 and back down
    trace.steps.append(Step("Router", 1, "receive", "receive the bits from link 1", size))
    if sizes[2]:
        stack.pop(0)
        size -= sizes[2]
        trace.steps.append(Step("Router", 2, "remove", f"check and remove {sizes[2]} B header", size,
                                -sizes[2]))
    net = next((h for h in stack if h.layer == 3), None)
    note = "read dst address, TTL 64 -> 63, pick link 2" if net else "pick link 2"
    if net:
        net.fields = _fields(3, 2)
    trace.steps.append(Step("Router", 3, "process", note, size))
    if out_sizes[2]:
        stack.insert(0, Header(2, out_sizes[2], _fields(2, 2)))
        size += out_sizes[2]
        trace.steps.append(Step("Router", 2, "add", f"add new {out_sizes[2]} B header for link 2",
                                size, out_sizes[2]))
    trace.steps.append(Step("Router", 1, "send", "send the bits on link 2", size))
    trace.links["link 2"] = [Header(h.layer, h.size, dict(h.fields)) for h in stack]

    # Yoshi: up the stack
    trace.steps.append(Step("Yoshi", 1, "receive", "receive the bits from link 2", size))
    for layer in range(2, 8):
        if stack and stack[0].layer == layer:
            h = stack.pop(0)
            size -= h.size
            trace.steps.append(Step("Yoshi", layer, "remove", f"read and remove {h.size} B header",
                                    size, -h.size))
        else:
            trace.steps.append(Step("Yoshi", layer, "pass", "pass up (no header)", size))
    trace.highest_layer = {"Zoya": 7, "Router": ROUTER_LAYERS, "Yoshi": 7}
    return trace
