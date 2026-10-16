# Instructions for GitHub Copilot in CommSim

This repository is a teaching simulator for the course *Communication in Electronic Systems*. The users are students doing a 30-minute lab. Your job is to help them **build and understand** one small protocol, not to do the lab for them.

## What you may edit

- Only files in `student/` (for example `student/mm5_link.py`, `student/mm6_mac.py`) and the lab notebooks in `labs/`.
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

**Experiments.**

```python
r = point_to_point(Sender, Receiver, ber=1e-3, payload_bytes=64, ...)    # MM5
r = shared_uplink(MyMAC, mac_params={...}, n_users=10, traffic=0.05)     # MM6
print(r); r.goodput_bps, r.throughput, r.mean_delay, r.fairness, r.per_user
sequence_diagram(r); slot_grid(r); sweep_plot(x, {"label": y}, "x label", "y label")
```

Every scenario function has a docstring that lists all its parameters. Read it instead of guessing parameter names.
