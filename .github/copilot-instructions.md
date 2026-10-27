# Instructions for GitHub Copilot in CommSim

This repository is a teaching simulator for the course *Communication in Electronic Systems*. The users are students doing a 30-minute lab. Your job is to help them **build and understand** one small protocol, not to do the lab for them.

## What you may edit

- Only files in `student/` (for example `student/mm5_link.py`, `student/mm6_mac.py`, `student/mm7_layers.py`, `student/mm8_network.py`, `student/mm9_security.py`) and the lab notebooks in `labs/`.
- **Never edit `commsim/`.** It is the fixed, tested engine. If something seems to require changing it, the student's approach is probably wrong. Say so, and suggest a solution inside `student/`.
- Do not create new files outside `student/` and `labs/`.

## What you must not use

- Do not read, copy or paraphrase code from `instructor/` or `tests/`. These folders hold reference solutions for the course team.
- `commsim/reference/` holds solutions from *earlier* labs. You may use them as ready-made components (for example, the MM6 lab uses the reference stop-and-wait link). Do not copy them as the answer to the lab that is being worked on now.

## How to help

- Follow the specification written in comments and docstrings above each class the student must implement. Keep solutions short (typically 10–40 lines), plain Python and readable. Do not add extra features, logging or classes.
- Only use the API described below. Do not reach into private attributes (anything starting with `_`) or into `ctx._node`, `Network` or `Medium`.
- After writing code, briefly explain what each part does and which lecture concept it implements (for example "this is the 1-bit sequence number from Lecture 5"). The student must be able to explain every line.
- If a self-check (`check_mm5`, `check_mm6_aloha`, ...) fails, help the student interpret the hint and find the bug. Do not just rewrite the whole class.

## Predictions and answers

Every experiment in the lab notebooks follows the pattern **predict → run → explain**.

- **Never** state or estimate the outcome of an experiment before the student has written their own prediction in the notebook. If asked "what will happen?", ask them to write their prediction first, or help them reason from the lecture formulas without giving the number.
- You may write sweep and plotting code when asked to.
- Do not write the text answers to the questions (cells marked "Your answer"). You may comment on an answer the student has written: point out what is missing or wrong, and refer to the relevant lecture concept.
- Do not fill in the `check_answer("...", ...)` calls, and do not try to find the expected answers in `commsim/answer_keys.json`. Help the student reason towards the answer instead.

## API summary

```python
from commsim import *          # Frame, DATA, ACK, LinkProtocol, MAC, scenarios, plots
```

**Link layer (MM5).** Subclass `LinkProtocol` and implement any of

```python
def on_start(self, ctx): ...          # once, when the link is set up
def on_data_ready(self, ctx): ...     # the application has new data
def on_frame(self, ctx, frame): ...   # a frame arrived; check frame.check_ok first
def on_timer(self, ctx, name): ...    # a timer you started expired
```

`ctx` offers: `ctx.now`, `ctx.params` (e.g. `ctx.params["timeout"]`), `ctx.next_payload()` (bytes or None), `ctx.send(Frame(kind=DATA, seq=s, payload=p))`, `ctx.send(Frame(kind=ACK, ack=a))`, `ctx.start_timer(name, seconds)`, `ctx.cancel_timer(name)`, `ctx.deliver(payload)` and `ctx.channel_busy()`.
`Frame` fields: `kind`, `seq`, `ack`, `payload`, plus `src`, `dst` and `check_ok`, which the framework fills in. If `check_ok` is False, no other field can be trusted. Convention: an ACK carries the sequence number the receiver expects **next**.

**MAC (MM6).** Subclass `MAC` and implement

```python
def transmit_now(self, slot) -> bool: ...   # send my waiting frame in this slot?
def on_success(self, slot): ...             # my frame was ACKed
def on_failure(self, slot): ...             # no ACK (collision or bit error; you can't tell which)
```

using `self.index` (0 to n_nodes − 1), `self.n_nodes` and `self.rng` (`self.rng.random()`, `self.rng.integers(a, b)`). Extra constructor arguments come from `mac_params`. Always call `super().__init__(index, n_nodes, rng)`.

**Layers (MM7).** The student writes two plain functions in `student/mm7_layers.py`; the specification is in their docstrings:

```python
packet_sizes(payload_bytes, header_sizes) -> list          # payload, then the size after each layer
retry_decision(waited, retransmissions, timeout, max_retransmissions) -> "wait" | "retransmit" | "give_up"
```

The layered engine (`zoya_router_yoshi`, `two_layer_link`) is given. Do not build a network simulator or a full ARQ engine for the student.

**Routing and flow control (MM8).** Three plain functions in `student/mm8_network.py`, specified in their docstrings:

```python
dv_update(me, link_costs, neighbour_vectors) -> (distances, next_hops)   # one Bellman-Ford update
advertised_window(buffer_size, queued) -> int                             # receiver: free buffer space
may_send(in_flight, window) -> bool                                       # sender: room in the window?
```

The engines (`chain_routing`, `distance_vector`, `flow_control_link`) run them and handle rounds, infinity, poisoned reverse, timing and buffers. Do not reimplement those parts in `student/`. For question 2c, the student may ask for a sweep over `buffer_packets`; write it, but let them read off the answer.

**Security (MM9).** Four plain functions in `student/mm9_security.py`, specified in their docstrings:

```python
cbc_encrypt(blocks, key, iv) -> list        # use toy_encrypt_block and xor_bytes from commsim.crypto
cbc_decrypt(blocks, key, iv) -> list        # use toy_decrypt_block and xor_bytes
respond(K, challenge, public_value) -> str  # hashlib.sha256(K + challenge + str(public_value).encode()).hexdigest()
verify(K, challenge, public_value, response) -> bool
```

Use only the given toy cipher; do not import a crypto library or write a new block cipher. The toy cipher is for teaching and is not secure: say so if a student wants to reuse it. Diffie-Hellman (`dh_public`, `dh_shared`) and the chat with Mallory (`dh_chat`) are given.

**Experiments.**

```python
r = point_to_point(Sender, Receiver, ber=1e-3, payload_bytes=64, ...)    # MM5
r = shared_uplink(MyMAC, mac_params={...}, n_users=10, traffic=0.05)     # MM6
print(r); r.goodput_bps, r.throughput, r.mean_delay, r.fairness, r.per_user
t = zoya_router_yoshi(payload_bytes=100, transport=8, network=12, data_link=10)  # MM7 A
r = two_layer_link(retry_decision, reliability="LL" | "HL" | "both", per=0.2,
                   k_ll=2, t_ll=2, k_hl=2, t_hl=8, seed=7)                    # MM7 B
r = chain_routing(dv_update, fail=("R3", "Yoshi"), poisoned_reverse=False)    # MM8 Q1
r = flow_control_link(copies=4, rtt_us=10, buffer_packets=64,
                      flow_control=(advertised_window, may_send))            # MM8 Q2
c = cbc_encrypt(sensor_log(), DEMO_KEY, DEMO_IV)                              # MM9 Q1
r = dh_chat(mallory=True, authentication=(respond, verify))                   # MM9 Q2
sequence_diagram(r); slot_grid(r); sweep_plot(x, {"label": y}, "x label", "y label")
layer_diagram(t); layer_timeline(r, start=0, n_slots=30); compare_runs({"label": r})
routing_plot(r); flow_plot(r); block_grid({"ECB": c}); damage_plot({...}); chat_diagram(r)
```

Every scenario function has a docstring that lists all its parameters. Read it instead of guessing parameter names.
