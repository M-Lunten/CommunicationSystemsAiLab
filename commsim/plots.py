"""Plots for the labs: sequence diagrams (MM5), slot grids (MM6) and parameter sweeps."""
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
STATUS = {"ok": "#0ca30c", "error": "#fab219", "collision": "#d03b3b", "lost": "#8a8984",
          "idle": "#e9e8e4"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#dcdbd6"


def _style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def sequence_diagram(results, max_frames=12, ax=None):
    """Alice on the left, Bob on the right, time running downwards (point_to_point runs)."""
    net = results.net
    log = net.medium.log[:max_frames]
    if not log:
        raise ValueError("nothing was transmitted")
    names = {a: n.name for a, n in net.nodes.items()}
    left = min(net.nodes)
    prop = net.medium.prop
    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 0.55 * len(log) + 1.5))
    end = max(tx.t1 + prop for tx in log)
    for x, addr in ((0, left), (1, [a for a in net.nodes if a != left][0])):
        ax.plot([x, x], [0, end], color=MUTED, linewidth=2)
        ax.text(x, -0.03 * end, names[addr], ha="center", va="bottom", fontsize=11,
                fontweight="bold", color=INK)
    for tx in log:
        x0, x1 = (0, 1) if tx.sender == left else (1, 0)
        colour = STATUS.get(tx.outcome, MUTED)
        ax.fill([x0, x1, x1, x0], [tx.t0, tx.t0 + prop, tx.t1 + prop, tx.t1], color=colour,
                alpha=0.35, linewidth=0)
        ax.plot([x0, x1], [tx.t0, tx.t0 + prop], color=colour, linewidth=2)
        f = tx.frame
        label = f"DATA seq={f.seq}" if f.kind == "DATA" else f"ACK ack={f.ack}"
        ax.text(0.5, (tx.t0 + tx.t1) / 2 + prop / 2, f"{label}  [{tx.outcome}]", ha="center",
                va="center", fontsize=8.5, color=INK,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    ax.set_ylim(end * 1.02, -0.08 * end)
    ax.set_xlim(-0.25, 1.25)
    ax.set_xticks([])
    ax.set_ylabel("time (s)", color=MUTED)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9)
    handles = [Patch(color=STATUS[k], alpha=0.6, label=k) for k in ("ok", "error", "lost")]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3,
              frameon=False, fontsize=9)
    ax.set_title("Sequence diagram", color=INK, fontsize=12, loc="left")
    return ax


def slot_grid(results, n_slots=40, start=0, ax=None):
    """One row per user, one column per slot (shared_uplink runs)."""
    net = results.net
    users = [n for n in net.nodes.values() if n.mac is not None]
    rows = {n.addr: i + 1 for i, n in enumerate(users)}
    slots = range(start, start + n_slots)
    per_slot = {k: [] for k in slots}
    for tx in net.medium.log:
        if tx.slot in per_slot:
            per_slot[tx.slot].append(tx)
    if ax is None:
        _, ax = plt.subplots(figsize=(min(14, 0.3 * n_slots + 2), 0.45 * (len(users) + 1) + 1.2))
    for col, k in enumerate(slots):
        txs = per_slot[k]
        channel = "idle" if not txs else ("collision" if len(txs) > 1 else txs[0].outcome)
        ax.add_patch(plt.Rectangle((col + 0.05, 0.05), 0.9, 0.9, color=STATUS[channel]))
        for tx in txs:
            ax.add_patch(plt.Rectangle((col + 0.05, rows[tx.sender] + 0.05), 0.9, 0.9,
                                       color=STATUS[tx.outcome]))
    ax.set_xlim(0, n_slots)
    ax.set_ylim(len(users) + 1, 0)
    ax.set_yticks([i + 0.5 for i in range(len(users) + 1)])
    ax.set_yticklabels(["channel"] + [n.name for n in users], fontsize=9, color=INK)
    step = max(1, n_slots // 10)
    ax.set_xticks([c + 0.5 for c in range(0, n_slots, step)])
    ax.set_xticklabels([str(start + c) for c in range(0, n_slots, step)], fontsize=8, color=MUTED)
    ax.set_xlabel("slot", color=MUTED)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(length=0)
    handles = [Patch(color=STATUS[k], label=lbl) for k, lbl in
               (("ok", "success"), ("collision", "collision"), ("error", "bit error"),
                ("idle", "idle"))]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False,
              fontsize=9)
    ax.set_title(results.scenario, color=INK, fontsize=10, loc="left")
    return ax


def sweep_plot(x, curves, xlabel, ylabel, title=None, logx=False, logy=False, ax=None,
               markers=True):
    """Plot several y-series against one x. `curves` is {label: list_of_y}.
    A label starting with 'theory' is drawn as a dashed line without markers."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    for i, (label, y) in enumerate(curves.items()):
        theory = label.lower().startswith("theory")
        ax.plot(x, y, label=label, color=SERIES[i % len(SERIES)], linewidth=2,
                linestyle="--" if theory else "-",
                marker=None if (theory or not markers) else "o", markersize=5)
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    if title:
        ax.set_title(title, color=INK, fontsize=12, loc="left")
    _style(ax)
    if len(curves) > 1:
        ax.legend(frameon=False, fontsize=9)
    return ax


# ---------------------------------------------------------------- MM7: layering

LAYER_COLOURS = {7: "#4a3aa7", 6: "#e87ba4", 5: "#eda100", 4: "#2a78d6", 3: "#eb6834",
                 2: "#1baf7a", 1: "#8a8984"}
PAYLOAD_COLOUR = "#c9c8c3"


def layer_diagram(trace, ax=None):
    """Zoya, the router and Yoshi as protocol stacks, the path of the packet through them,
    and the packet as it looks on each link (zoya_router_yoshi runs)."""
    from .stack import LAYERS, SHORT
    if ax is None:
        fig = plt.figure(figsize=(11, 7.2))
        ax = fig.add_axes([0.02, 0.30, 0.96, 0.66])
        bar_ax = fig.add_axes([0.10, 0.04, 0.84, 0.20])
    else:
        bar_ax = None
    cols = {"Zoya": 0.0, "Router": 3.2, "Yoshi": 6.4}
    w, h = 1.3, 0.72
    for node, x in cols.items():
        top = trace.highest_layer[node]
        for layer in range(1, top + 1):
            ax.add_patch(plt.Rectangle((x - w / 2, layer - h / 2), w, h, color=LAYER_COLOURS[layer],
                                       alpha=0.18, linewidth=0))
            ax.text(x, layer, f"L{layer} {LAYERS[layer]}", ha="center", va="center", fontsize=8.5,
                    color=INK)
        ax.text(x, 7.75, node, ha="center", va="bottom", fontsize=12, fontweight="bold", color=INK)
    # the path of the packet
    rx = cols["Router"]
    path = ([(cols["Zoya"] + w / 2 + 0.08, 7.3), (cols["Zoya"] + w / 2 + 0.08, 0.5),
             (rx - w / 2 - 0.08, 0.5), (rx - w / 2 - 0.08, 3.3), (rx + w / 2 + 0.08, 3.3),
             (rx + w / 2 + 0.08, 0.5), (cols["Yoshi"] - w / 2 - 0.08, 0.5),
             (cols["Yoshi"] - w / 2 - 0.08, 7.3)])
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.6, shrinkA=0, shrinkB=0))
    ax.text((cols["Zoya"] + rx) / 2, 0.32, "link 1", ha="center", va="top", fontsize=9, color=MUTED)
    ax.text((rx + cols["Yoshi"]) / 2, 0.32, "link 2", ha="center", va="top", fontsize=9, color=MUTED)
    # what happens at each layer
    for s in trace.steps:
        if s.action in ("send", "receive"):
            continue
        x = cols[s.node]
        if s.node == "Zoya":
            tx, ha = x - w / 2 - 0.1, "right"
        elif s.node == "Yoshi":
            tx, ha = x + w / 2 + 0.1, "left"
        else:
            tx, ha = x + w / 2 + 0.25, "left"
        if s.action == "pass":
            text = f"{s.size} B"
        elif s.action in ("add", "remove"):
            text = f"{s.delta:+d} B -> {s.size} B"
        else:
            text = s.note.replace(", ", "\n", 1)
        y = s.layer + (0.18 if (s.node == "Router" and s.action == "remove") else
                       -0.18 if (s.node == "Router" and s.action == "add") else 0)
        if s.node == "Router" and s.layer == 3:
            y += 0.55
        ax.text(tx, y, text, ha=ha, va="center", fontsize=8,
                color=LAYER_COLOURS[s.layer] if s.action in ("add", "remove") else MUTED)
    ax.set_xlim(-2.6, 9.0)
    ax.set_ylim(0.0, 8.2)
    ax.axis("off")
    ax.set_title(f"{trace.payload_bytes} B of data from Zoya to Yoshi:  {trace.packet_bytes} B on link 1, "
                 f"payload efficiency {trace.efficiency:.2f}", color=INK, fontsize=11, loc="left")
    if bar_ax is not None:
        _packet_bars(trace, bar_ax, SHORT)
    return ax


def _packet_bars(trace, ax, short):
    before = {h.layer: h for h in trace.links["link 1"]}
    rewritten = {s.layer for s in trace.steps if s.node == "Router" and s.action == "add"}
    for row, link in enumerate(("link 1", "link 2")):
        x = 0
        for hdr in trace.links[link]:
            hatch = None
            if link == "link 2":
                if hdr.layer in rewritten:
                    hatch = "//"           # a new header for this link
                elif before[hdr.layer].fields != hdr.fields:
                    hatch = ".."           # same header, one field updated
            ax.barh(row, hdr.size, left=x, color=LAYER_COLOURS[hdr.layer], alpha=0.85, hatch=hatch,
                    edgecolor="white", height=0.6)
            ax.text(x + hdr.size / 2, row, f"{short[hdr.layer]} {hdr.size}", ha="center", va="center",
                    fontsize=7.5, color="white", fontweight="bold")
            x += hdr.size
        ax.barh(row, trace.payload_bytes, left=x, color=PAYLOAD_COLOUR, height=0.6, edgecolor="white")
        ax.text(x + trace.payload_bytes / 2, row, f"data {trace.payload_bytes}", ha="center",
                va="center", fontsize=8, color=INK)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["link 1", "link 2"], fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel("bytes on the link.  On link 2:  //  new header written by the router,"
                  "  ..  same header, a field updated", color=MUTED, fontsize=9)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)


EVENT_STYLE = {   # kind: (colour, legend label)
    "hl_send": ("#2a78d6", "HL sends new packet"),
    "hl_retx": ("#eda100", "HL retransmission"),
    "hl_retx_premature": ("#d03b3b", "HL retransmission while LL still busy"),
    "hl_ack": ("#008300", "HL ACK received"),
    "hl_give_up": (INK, "gives up"),
    "tx_ok": (STATUS["ok"], "LL frame arrives"),
    "tx_lost": (STATUS["lost"], "LL frame lost"),
    "ll_give_up": (INK, None),
    "deliver": (STATUS["ok"], None),
    "duplicate": ("#eb6834", "duplicate at Yoshi's HL"),
}


def layer_timeline(results, n_slots=30, start=0, ax=None):
    """One row per layer (Zoya HL, Zoya LL, Yoshi LL, Yoshi HL), one column per slot
    (two_layer_link runs). Labels are HL packet numbers; 3' is the HL's retransmission of
    packet 3, A3 is the HL ACK for packet 3. Small marks under an LL cell: an LL ACK sent
    (green: arrived, grey x: lost)."""
    rows = ["Zoya HL", "Zoya LL", "Yoshi LL", "Yoshi HL"]
    slots = range(start, start + n_slots)
    cells, marks = {}, {}
    for e in results.events:
        if e.slot not in slots or e.kind == "ll_ack":
            continue
        if e.kind in ("ack_ok", "ack_lost"):
            marks[(e.row, e.slot)] = e.kind
        else:
            cells.setdefault((e.row, e.slot), []).append(e)
    if ax is None:
        _, ax = plt.subplots(figsize=(min(15, 0.42 * n_slots + 2.5), 3.4))
    for (row, slot), events in cells.items():
        r, col = rows.index(row), slot - start
        width = 0.9 / len(events)
        for i, e in enumerate(events):
            colour = EVENT_STYLE[e.kind][0]
            x = col + 0.05 + i * width
            ax.add_patch(plt.Rectangle((x, r + 0.08), width, 0.72, color=colour,
                                       alpha=0.55 if e.kind == "tx_lost" else 0.9))
            label = "x" + e.label if e.kind in ("hl_give_up", "ll_give_up") else e.label
            ax.text(x + width / 2, r + 0.44, label, ha="center", va="center",
                    fontsize=7 if len(events) == 1 else 6, color="white", fontweight="bold")
    for (row, slot), kind in marks.items():
        r, col = rows.index(row), slot - start
        ax.plot(col + 0.5, r + 0.9, marker="^" if kind == "ack_ok" else "x", markersize=4,
                color=STATUS["ok"] if kind == "ack_ok" else STATUS["lost"])
    for r in range(1, len(rows)):
        ax.axhline(r, color=GRID, linewidth=0.8)
    ax.axhline(2, color=MUTED, linewidth=1.2, linestyle="--")
    ax.set_xlim(0, n_slots)
    ax.set_ylim(len(rows), 0)
    ax.set_yticks([i + 0.45 for i in range(len(rows))])
    ax.set_yticklabels(rows, fontsize=9, color=INK)
    step = max(1, n_slots // 15)
    ax.set_xticks([c + 0.5 for c in range(0, n_slots, step)])
    ax.set_xticklabels([str(start + c) for c in range(0, n_slots, step)], fontsize=8, color=MUTED)
    ax.set_xlabel("slot", color=MUTED)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(length=0)
    handles = [Patch(color=c, label=l) for c, l in EVENT_STYLE.values() if l]
    handles += [Line2D([], [], marker="^", linestyle="none", color=STATUS["ok"], markersize=5,
                       label="LL ACK sent, arrives"),
                Line2D([], [], marker="x", linestyle="none", color=STATUS["lost"], markersize=5,
                       label="LL ACK sent, lost")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=8)
    ax.set_title(results.scenario, color=INK, fontsize=9.5, loc="left")
    return ax


# ---------------------------------------------------------------- MM8: routing and flow control

def routing_plot(results, ax=None):
    """Each router's distance to the destination, before the failure and after every round
    (distance_vector / chain_routing runs). The dashed line is infinity. Lines are shifted
    up or down a little so that routers with the same distance stay visible."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7.5, 3.8))
    rounds = list(range(len(results.history) + 1))
    nodes = [n for n in results.nodes if n != results.destination]
    for i, n in enumerate(nodes):
        shift = 0.12 * (i - (len(nodes) - 1) / 2)
        ax.plot(rounds, [d + shift for d in results.distances(n)], label=n, color=SERIES[i % len(SERIES)],
                linewidth=2, marker="o", markersize=4, drawstyle="steps-post")
    ax.axhline(results.infinity, color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(rounds[-1], results.infinity, " infinity (unreachable)", va="bottom", ha="right",
            fontsize=8, color=MUTED)
    ax.set_xticks(rounds)
    ax.set_xticklabels(["before"] + [str(r) for r in rounds[1:]], fontsize=8)
    ax.set_xlabel("round after the failure", color=MUTED)
    ax.set_ylabel(f"distance to {results.destination}", color=MUTED)
    ax.set_ylim(0, results.infinity + 1.5)
    ax.set_title(results.scenario, color=INK, fontsize=10, loc="left")
    _style(ax)
    ax.legend(frameon=False, fontsize=9, loc="center left", bbox_to_anchor=(1.0, 0.5))
    return ax


def flow_plot(results, ax=None):
    """Packets in the receiver buffer at the start of the run, with drops marked
    (flow_control_link runs)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3.4))
    tr = results.trace
    if not tr:
        raise ValueError("nothing was traced: no packet arrived in the first trace_ns")
    t = [x[0] / 1000 for x in tr]
    q = [x[1] for x in tr]
    ax.step(t, q, where="post", color=SERIES[0], linewidth=1.8, label="packets in the buffer")
    drops = [(x[0] / 1000, x[1]) for x in tr if x[2] == "drop"]
    if drops:
        ax.plot(*zip(*drops), linestyle="none", marker="x", color=STATUS["collision"], markersize=6,
                label="dropped packet")
    ax.axhline(results.params["buffer_packets"], color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(t[-1], results.params["buffer_packets"], "buffer size ", ha="right", va="bottom",
            fontsize=8, color=MUTED)
    ax.set_ylim(0, results.params["buffer_packets"] * 1.2 + 1)
    ax.set_xlabel("time (µs)", color=MUTED)
    ax.set_ylabel("packets in the buffer", color=MUTED)
    ax.set_title(results.scenario, color=INK, fontsize=9, loc="left")
    _style(ax)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    return ax


# ---------------------------------------------------------------- MM9: security

def block_grid(panels, cols=8):
    """What Eve sees: every block as a coloured square, one colour per different block value.
    `panels` is {title: list_of_blocks}. Equal blocks get equal colours (within a panel)."""
    import matplotlib.colors as mcolors
    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(3.4 * n, 3.6))
    axes = [axes] if n == 1 else axes
    palette = SERIES + ["#5e9fe6", "#f29c6f", "#6fd0a8", "#f4c45a"]
    for ax, (title, blocks) in zip(axes, panels.items()):
        values = list(dict.fromkeys(blocks))
        rows = -(-len(blocks) // cols)
        for i, b in enumerate(blocks):
            k = values.index(b)
            if len(values) <= len(palette):
                colour = palette[k]
            else:
                h = int.from_bytes(b[:3], "big") / 2 ** 24
                colour = mcolors.hsv_to_rgb((h, 0.55, 0.85))
            ax.add_patch(plt.Rectangle((i % cols + 0.05, i // cols + 0.05), 0.9, 0.9, color=colour))
        ax.set_xlim(0, cols)
        ax.set_ylim(rows, 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{title}\n{len(values)} different blocks", color=INK, fontsize=10)
    return axes


def damage_plot(cases, n_blocks=None):
    """Which plaintext blocks arrive damaged. `cases` is {label: list_of_damaged_indices};
    pass n_blocks for the total number of blocks."""
    n_blocks = n_blocks or (max((max(v) for v in cases.values() if v), default=0) + 1)
    fig, ax = plt.subplots(figsize=(min(14, 0.2 * n_blocks + 2.5), 0.45 * len(cases) + 1.0))
    for r, (label, bad) in enumerate(cases.items()):
        for i in range(n_blocks):
            ax.add_patch(plt.Rectangle((i + 0.08, r + 0.12), 0.84, 0.76,
                                       color=STATUS["collision"] if i in bad else STATUS["ok"],
                                       alpha=0.9 if i in bad else 0.35))
    ax.set_xlim(0, n_blocks)
    ax.set_ylim(len(cases), 0)
    ax.set_yticks([r + 0.5 for r in range(len(cases))])
    ax.set_yticklabels([f"{k}  ({len(v)} damaged)" for k, v in cases.items()], fontsize=9, color=INK)
    ax.set_xticks([i + 0.5 for i in range(0, n_blocks, 4)])
    ax.set_xticklabels([str(i) for i in range(0, n_blocks, 4)], fontsize=8, color=MUTED)
    ax.set_xlabel("plaintext block", color=MUTED)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(length=0)
    return ax


def chat_diagram(results, max_messages=4, ax=None):
    """Message sequence chart of a dh_chat run: Zoya, the router (or Mallory), Yoshi."""
    mid = "Mallory" if results.mallory else "Router"
    xs = {"Zoya": 0, mid: 1, "Yoshi": 2}
    rows = [e for e in results.transcript if e[4] == "key"]
    data = [e for e in results.transcript if e[4] == "data"][:2 * max_messages]
    rows += data
    if ax is None:
        _, ax = plt.subplots(figsize=(7.5, 0.42 * len(rows) + 1.4))
    for name, x in xs.items():
        colour = STATUS["collision"] if name == "Mallory" else MUTED
        ax.plot([x, x], [0, len(rows) + 0.3], color=colour, linewidth=2)
        ax.text(x, -0.35, name, ha="center", va="bottom", fontsize=11, fontweight="bold",
                color=STATUS["collision"] if name == "Mallory" else INK)
    for y, (_, frm, to, label, kind) in enumerate(rows, start=1):
        colour = SERIES[0] if kind == "key" else SERIES[2]
        ax.annotate("", xy=(xs[to], y), xytext=(xs[frm], y),
                    arrowprops=dict(arrowstyle="-|>", color=colour, linewidth=1.4))
        ax.text((xs[frm] + xs[to]) / 2, y - 0.12, label, ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_ylim(len(rows) + 0.6, -0.8)
    ax.set_xlim(-0.3, 2.3)
    ax.axis("off")
    status = ("" if results.handshake_ok is None else
              "   handshake OK" if results.handshake_ok else "   handshake REJECTED")
    ax.set_title(results.scenario + status, color=INK, fontsize=9, loc="left")
    return ax
