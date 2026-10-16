# CommSim

The course simulator for **Communication in Electronic Systems**. One framework that grows with the course: every lecture adds a layer, and you build the interesting part of that layer yourself.

| Lecture | You build | File |
|---|---|---|
| MM5 | stop-and-wait ARQ (link layer) | `student/mm5_link.py` |
| MM6 | medium access control (MAC) | `student/mm6_mac.py` |
| MM7 | a packet-size helper and a retry rule, used by a given layered stack | `student/mm7_layers.py` |

Each lab takes about **30 minutes**, after the regular exercises.

## Setup (once, about 5 minutes)

1. Install Python 3.10 or newer, and VS Code with the **Python**, **Jupyter** and **GitHub Copilot** extensions. (Copilot is free for students through GitHub Education.)
2. Open the `CommSim` folder in VS Code, open a terminal and run:
   ```
   pip install -r requirements.txt
   ```
3. Open `labs/MM5_lab.ipynb` (or the lab for this week) and run the first cell.

## Rules

- You only change files in `student/` and your lab notebook. `commsim/` is the fixed engine: don't edit it. Copilot already knows this rule (see `.github/copilot-instructions.md`).
- Write your prediction **before** you run an experiment.
- Use Copilot to write code, but you must be able to explain every line.

## How it fits together

```
 application       creates payloads (sender) and checks what arrives (receiver)
 link layer        your LinkProtocol: frames, ACKs, retransmission        <- MM5
 MAC               your MAC: when may I use the shared channel?           <- MM6
 medium + PHY      delays, collisions, bit errors (Binary Symmetric Channel)
```

Frames are real bits: preamble, header, payload and check bits. A bit error can hit any field, including the length field or the CRC.

## Cheat sheet

**Link layer (MM5)**: subclass `LinkProtocol` and fill in

```python
def on_start(self, ctx): ...          # once, at the start
def on_data_ready(self, ctx): ...     # the application has new data
def on_frame(self, ctx, frame): ...   # a frame arrived (check frame.check_ok!)
def on_timer(self, ctx, name): ...    # a timer you started expired
```

using `ctx.next_payload()`, `ctx.send(Frame(kind=DATA, seq=s, payload=p))`, `ctx.send(Frame(kind=ACK, ack=a))`, `ctx.start_timer("name", seconds)`, `ctx.cancel_timer("name")`, `ctx.deliver(payload)` and `ctx.params["timeout"]`.

**MAC (MM6)**: subclass `MAC` and fill in

```python
def transmit_now(self, slot): ...     # True = send my waiting frame in this slot
def on_success(self, slot): ...       # my frame was ACKed
def on_failure(self, slot): ...       # no ACK (collision or bit error)
```

using `self.index`, `self.n_nodes` and `self.rng.random()`.

**Layers (MM7)**: fill in two functions

```python
packet_sizes(payload_bytes, header_sizes)        # -> [payload, after layer 1, after layer 2, ...]
retry_decision(waited, retransmissions, timeout, max_retransmissions)   # -> "wait" | "retransmit" | "give_up"
```

and check short answers with `check_answer("A1", your_answer)`.

**Experiments**

```python
r = point_to_point(MySender, MyReceiver, ber=1e-3)        # MM5: Alice -> Bob
r = shared_uplink(MyMAC, n_users=10, traffic=0.05)        # MM6: users -> Basil
t = zoya_router_yoshi(payload_bytes=100, network=12)      # MM7 A: Zoya -> router -> Yoshi
r = two_layer_link(retry_decision, reliability="both", per=0.2, t_hl=4)   # MM7 B: HL over LL
print(r)                       # all metrics
r.goodput_bps, r.throughput, r.mean_delay, r.fairness, r.per_user
sequence_diagram(r); slot_grid(r); sweep_plot(x, {"label": y}, "x", "y")
layer_diagram(t); layer_timeline(r); compare_runs({"label": r, ...})
```

Every scenario function has a docstring: hover over it in VS Code to see all parameters.

## When something goes wrong

- **You changed `student/...py` but nothing happened:** the notebook reloads it automatically when you run a cell; if not, restart the kernel.
- **NotImplementedError:** that part of the lab is not done yet.
- **A self-check fails:** read its hint. It tells you *what* is wrong, not how to fix it.
- **The simulation never ends:** your sender probably never stops retransmitting, or never moves on after an ACK.
