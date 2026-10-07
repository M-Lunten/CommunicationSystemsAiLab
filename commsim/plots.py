"""Plots for the labs: sequence diagrams (MM5), slot grids (MM6) and parameter sweeps."""
import matplotlib.pyplot as plt
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
