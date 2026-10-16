# CommSim: instructor overview

*A pilot for MM5–MM7 of Communication in Electronic Systems, built to show how one simulation framework could grow with Part 2 of the course.*

## The idea

Students get **one framework for the whole of Part 2**. The course team writes and tests the engine: time, channel, collisions, bit errors, metrics and plots. In each lecture, students build **one small, clearly marked piece** with help from GitHub Copilot: the link layer in MM5, the MAC in MM6, and so on. They then use it to answer questions that are unrealistic on paper, because they need thousands of frames or a parameter sweep.

Each lab takes **about 30 minutes**, after the regular exercises. The pieces students build stay in the framework, so by the end of the course they have a full protocol stack that they wrote themselves.

## Why this is not "just prompting"

- **Small editable part.** Students edit 20–50 lines in one file. A Copilot mistake breaks one method, not the tool, and a TA can read every group's code in a minute.
- **Fixed, tested engine.** `tests/test_theory.py` checks the engine against the course formulas: PER = 1 − (1 − BER)^n, the stop-and-wait transfer time, N·p·(1 − p)^(N−1) for slotted ALOHA, and the Problem Set 2, Problem 2(c) answer. `tests/test_mm7.py` checks the layer engine: residual loss PER^(K+1) and the expected number of ARQ attempts.
- **Self-checks.** `check_mm5()`, `check_mm6_aloha()`, `check_mm7_encapsulation()` and `check_mm7_retry()` tell a group *what* is wrong, with a hint, never the code. From MM7 on, `check_answer("A1", x)` gives instant feedback on short objective answers; the keys are stored as salted hashes in `commsim/answer_keys.json` (a deterrent, not a lock: yes/no answers can be guessed).
- **Copilot guardrails.** `.github/copilot-instructions.md` is read automatically by Copilot in VS Code. It limits edits to `student/`, describes the API, and asks Copilot not to give away experiment outcomes before the student has predicted them.
- **Questions that resist outsourcing.** Each experiment is: write a prediction, run it, explain the difference. Copilot can run the experiment, but the prediction and the explanation are the student's.
- **Different results per group** in the open parts (the frame-size choice, MAC designs, the challenge), which gives material for a short class discussion.

## What is in the folder

```
CommSim/
├── README.md                       for students: setup, rules, cheat sheet
├── INSTRUCTOR.md                   this file
├── .github/copilot-instructions.md guardrails Copilot reads automatically
├── commsim/                        the fixed engine (students never edit it)
│   ├── sim.py  phy.py  frames.py  medium.py  node.py  apps.py
│   ├── scenarios.py                point_to_point() for MM5, shared_uplink() for MM6
│   ├── stack.py                    MM7 A: zoya_router_yoshi(), the 7-layer packet walk
│   ├── twolayer.py                 MM7 B: two_layer_link(), ARQ at a higher and a lower layer
│   ├── results.py  plots.py  checks.py
│   ├── answers.py  answer_keys.json   check_answer() with hashed answer keys
│   └── reference/                  solutions released after each session (MM5: stop-and-wait, MM6: MACs)
├── student/
│   ├── mm5_link.py                 SOLVED in this example (as a group would leave it)
│   ├── mm6_mac.py                  SOLVED in this example
│   └── mm7_layers.py               as handed out for MM7
├── labs/
│   ├── MM5_lab.ipynb               completed example, with outputs and sample answers
│   ├── MM6_lab.ipynb               completed example, with outputs and sample answers
│   └── MM7_lab.ipynb               as handed out for MM7
├── instructor/
│   ├── starters/                   MM5 and MM6 as handed out (notebooks and student files)
│   └── preview/                    HTML exports of the executed labs (open in a browser)
├── tests/                          engine vs. lecture formulas
└── trial/                          NOT IN GIT: MM7 solutions, answers and the executed trial run
```

**State of this example:** MM5 and MM6 have been run: the student files and notebooks are answered, and the reference solutions are in `commsim/reference/`. MM7 is ready to hand out. Its solutions and expected answers are only in the gitignored `trial/` folder, so they never reach the public repo.

## What we give, and what students build

| | Given by the course | Built by students with Copilot |
|---|---|---|
| **MM5** | Engine; frames with real bits (preamble, length field, CRC); the Binary Symmetric Channel; the "Utopia" example protocol; `check_mm5` | `StopAndWaitSender` / `StopAndWaitReceiver`: ACKs, timeout, retransmission, 1-bit sequence number. Optional: a theory curve for experiment C2 |
| **MM6** | Slotted shared channel; the MM5 reference link on top; `AlwaysTransmit` and `RoundRobinTDMA` examples; traffic models (saturated, Bernoulli, bursty); `check_mm6_aloha` | `SlottedAloha`; then two of: a sweep over N, `GroupedAloha` (Problem 2c), `BackoffAloha`; optional `MyMAC` challenge |
| **MM7** | Zoya → router → Yoshi packet walk with a layer diagram; a two-layer (HL/LL) ARQ simulator in slots with a packet erasure channel, a timeline plot and per-layer counters; `check_mm7_encapsulation`, `check_mm7_retry`, `check_answer` | `packet_sizes` (packet size after each layer) and `retry_decision` (wait / retransmit / give up), used by both layers |

## MM5 session (30 min)

| Part | Min | Students do | What they find (from the executed example) |
|---|---|---|---|
| A | 5 | Run "Utopia" on the Problem Set 1 setup (79 × 64 B, 1 kbit/s, 10 ms), clean and with BER = 10⁻³ | Goodput 953 bit/s, close to their Problem 1(c) answer. At BER = 10⁻³ only 42/79 arrive intact and 37 corrupted payloads are delivered as if they were fine |
| B | 10 | Implement stop-and-wait ARQ in `student/mm5_link.py`, then run `check_mm5` | Without the sequence number, check 3 fails (91 duplicates when ACKs are lost). With it: 79/79, but goodput drops to 442 bit/s |
| C1 | 6–7 | Sweep payload size at two BERs | The best payload is about 128 B at 10⁻⁴ and about 32 B at 10⁻³. Problem 1(d)'s "bigger is more efficient" only holds on a clean channel |
| C2 | 6–7 | Sweep distance; optionally add a theory curve | Half the 1 Mbit/s link is wasted at about 50 km. Mars uses 10⁻⁶ of the link or less, which motivates sliding windows (MM8) |
| C3 | 6–7 | Count undetected errors for none / parity / CRC-8 / CRC-16 | Parity + ARQ delivers about 1500 corrupted payloads of 2000 at BER 3·10⁻²: retrying until a corrupted frame passes. CRC-16: 0 |
| D | 2 | Reflection | |

Students pick two of C1–C3. Each sweep runs in 1–13 seconds on a laptop.

## MM6 session (30 min)

| Part | Min | Students do | Expected finding |
|---|---|---|---|
| A | 5 | Run MM5's link on a shared channel with `AlwaysTransmit`, then with TDMA | 200 of 200 slots collide: deterministic retransmission deadlocks. TDMA fixes it, but needs N, an index and a coordinator |
| B | 8 | Implement `SlottedAloha`, then run `check_mm6_aloha` | Matches N·p·(1 − p)^(N−1) within 0.03 |
| C1 | 7 | Sweep p for N = 10; then fix p and sweep N (students write this sweep) | Too eager is worse than too shy. A fixed p collapses as N grows: random access still needs to know N |
| C2 | 7 | Implement `GroupedAloha`, check Problem 2(c), sweep all splits | 4 + 16 gives 0.40, as on paper. 1 + 19 maximises throughput (0.69) but fairness is 0.09: best throughput ≠ best system |
| C3 | 7 | Implement `BackoffAloha`; sweep load for three MACs | ALOHA wins on delay at low load. Slotted ALOHA saturates near 1/e. TDMA carries 0.7. Back-off "beats" 1/e by letting one user capture the channel (fairness 0.13) |
| D | 2 | Reflection; optional neighbourhood challenge (doorbells, sensors, streamer) | TDMA starves the streamer (worst user 37 %); back-off ALOHA reaches 90 % |

## MM7 session (30 min)

Built from the colleague's proposal and anchored in Problem Set 7. Rhythm: predict → run → observe → change one knob → answer and check. Expected answers are deliberately not listed here: see `trial/MM7_lab_trial.ipynb` (local only).

| Part | Min | Students do | Problem Set 7 |
|---|---|---|---|
| A0–A1 | 2 | Match service / protocol / interface; predict the highest layer the router processes | 1(b), 1(c) |
| A2–A3 | 4 | Run `zoya_router_yoshi`; read the layer diagram and the header-field table (link-specific vs. end-to-end) | 1(c) |
| A4–A5 | 6 | Copilot writes `packet_sizes`; total size and payload efficiency; change one header size at a time | 1(c) |
| B1 | 1 | Bits for the application id (16 apps) | 2(a) |
| task | 4 | Copilot writes `retry_decision`; `check_mm7_retry` | |
| B2–B3 | 5 | LL only, HL only, both, on the same channel: transmissions, delay, goodput, overhead | 2(b) |
| B4–B5 | 6 | T_HL = 4 against an LL that can need 6 slots: premature HL retries in the timeline; then T_HL = 7; free play | 2(c) |

All answers that depend on simulation use `seed=7`, so every group gets the same numbers. Problem 1(a) and 1(d) (why layering; cross-layer design) stay on paper.

**Trial run.** `.venv/bin/python trial/run_trial.py` regenerates `commsim/answer_keys.json` (B2 is computed from the simulation), runs the notebook as a student would in a sandbox with the solved student file, and runs the untouched handout to list the errors students see before writing code. Rerun it after any change to the engine or the notebook, then commit the new `answer_keys.json`.

## How it grows (MM8 onwards)

The interfaces that later lectures need are already in place: addresses in the frame header, a configurable number of sequence bits, a broadcast medium with a `promiscuous` flag, and a physical layer behind one `corrupt(bits)` method.

| Lecture | Framework adds | Students build | Question it unlocks |
|---|---|---|---|
| MM8 Network, transport | Routers with routing tables; a bottleneck queue | Distance-vector routing; sliding window, then AIMD congestion control | How large must the window be for Mars (MM5 C2 again)? Do two AIMD flows converge to a fair share? |
| MM9 Security | Eve, a node that hears everything on the medium | Encryption and an integrity tag between application and link; Diffie-Hellman over the simulated link | What can Eve read or change before and after? What does security cost in overhead? |
| MM10 Modulation, coding | `ModulatedChannel` replaces the bit-flip channel, behind the same interface | Mapper/demapper for BPSK, QPSK, 16-QAM; a simple channel code | BER vs. Eb/N0 compared with the Q-function formulas; MM5's best frame size, now as a function of SNR |
| MM11 Waveforms | Sample-level physical layer | Pulse shaping, matched filter | Eye diagrams, ISI, and their effect on everything above |
| MM12 Workshop | — | The full stack | End-to-end design under constraints |

After each session, the reference solution goes into `commsim/reference/`. The next lab uses it by default, so a group that didn't finish is never blocked.

## Practical notes

- **Setup:** Python 3.10+, VS Code with the Python, Jupyter and Copilot extensions, `pip install -r requirements.txt`. Recommend that students do this before the first session.
- **Run times:** the whole MM5 lab runs in about 20 s, MM6 in about 20 s, MM7 in a few seconds.
- **Preparation per lecture:** one engine extension, one student file with stubs and specifications, one notebook, one self-check, and tests against the lecture formulas. The whole engine for MM5 and MM6 is about 1,250 lines including comments.
- **Not yet tried with students.** Before rolling it out, it's worth a dry run with one or two students to check the 30-minute budget, especially how long Copilot takes on Part B.
- **Run the tests:** `python -m pytest tests` (about 7 s). The two-layer tests need the solved MM7 file in `trial/`, and are skipped without it.

## Small modelling choices to know about

- The frame has one more bit than Figure 1 in Problem Set 1 (a DATA/ACK type bit), so Problem 1 numbers differ slightly (537 vs. 536 bits).
- In MM6, a slot fits one DATA frame and its ACK. ACKs come from Basil on the same channel but never collide, because users only start transmitting at slot boundaries. A user cannot tell a collision from a bit error, as in practice.
- An ARQ timer starts when the frame actually goes on air, not when it is handed to the MAC.
- MM7 Part B runs in slots, separately from the MM5/MM6 bit-level engine: every frame (DATA or ACK) is lost with probability PER, one LL attempt takes 2 slots, and LL ACKs travel on a feedback channel next to the data. K counts *retransmissions* (Lecture 7 notes), so K_LL = 2 means at most 3 attempts. The LL is a stop-and-wait like the MM5 reference, extended with a retry limit; students' own MM5 classes do not plug in here.
- In MM7, an HL retransmission is *premature* if Zoya's LL still holds an earlier copy of that packet, and *unnecessary* if an earlier copy reached Yoshi anyway. With T_HL = 7, a few premature retries remain, because a new packet can wait in the LL queue behind a stale copy of the previous packet. This is worth mentioning when students ask.
