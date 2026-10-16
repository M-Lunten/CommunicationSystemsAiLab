"""Self-checks students run after implementing their part of a lab.

They say *what* is wrong and give a hint, never the code.
"""
from .scenarios import point_to_point, shared_uplink


def _report(name, ok, detail, hint):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        print(f"      hint: {hint}")
    return ok


def check_mm5(sender, receiver):
    """Checks a stop-and-wait ARQ implementation (Lab MM5, part B)."""
    results = []
    r = point_to_point(sender, receiver, n_packets=20, payload_bytes=8, rate_bps=10_000,
                       prop_delay=0.001, ber=0.0, check="crc16")
    results.append(_report(
        "1 perfect channel", r.delivered == 20 and r.duplicates == 0 and r.retransmissions == 0,
        f"{r.delivered}/20 delivered, {r.duplicates} duplicates, {r.retransmissions} retransmissions",
        "with no errors every frame should be sent once and ACKed. Does the sender move on "
        "to the next payload when the ACK arrives?"))
    r = point_to_point(sender, receiver, n_packets=200, payload_bytes=8, rate_bps=10_000,
                       prop_delay=0.001, ber=3e-3, check="crc16", seed=2)
    results.append(_report(
        "2 bit errors", r.delivered == 200 and r.undetected_errors == 0,
        f"{r.delivered}/200 delivered, {r.undetected_errors} corrupted",
        "some DATA frames arrive with check_ok == False. Does the receiver ignore them, and "
        "does the sender retransmit when its timer expires?"))
    r = point_to_point(sender, receiver, n_packets=200, payload_bytes=8, rate_bps=10_000,
                       prop_delay=0.001, ber=0.0, ack_loss=0.3, check="crc16", seed=3)
    results.append(_report(
        "3 lost ACKs", r.delivered == 200 and r.duplicates == 0,
        f"{r.delivered}/200 delivered, {r.duplicates} duplicates",
        "when an ACK is lost, Bob receives the same DATA frame again. How can he tell it "
        "is a copy and not new data (Lecture 5, 'ARQ with sequence number')? And does he "
        "still ACK the copy, so Alice can move on?"))
    print("\nAll checks passed." if all(results) else "\nFix the failing checks and run again.")
    return all(results)


def check_mm6_aloha(mac_class, tolerance=0.03):
    """Compares a slotted ALOHA MAC (parameter p) with N p (1-p)^(N-1) (Lab MM6, part B)."""
    ok = True
    for n, p in ((2, 0.5), (5, 0.2), (10, 0.1), (10, 0.3)):
        r = shared_uplink(mac_class, mac_params={"p": p}, n_users=n, n_slots=4000, seed=7)
        theory = n * p * (1 - p) ** (n - 1)
        ok &= _report(f"N={n:>2}, p={p}", abs(r.throughput - theory) <= tolerance,
                      f"simulated {r.throughput:.3f}, theory {theory:.3f}",
                      "in every slot where it has a frame, each node should transmit with "
                      "probability p, independently of the others and of what happened before.")
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok


def check_mm7_encapsulation(packet_sizes):
    """Checks the packet_sizes helper (Lab MM7, part A4)."""
    cases = [((50, [20, 20, 18]), [50, 70, 90, 108]),
             ((1000, [2, 2]), [1000, 1002, 1004]),     # Lecture 7: file length + file CRC
             ((64, [0, 4]), [64, 64, 68]),
             ((1, []), [1])]
    ok = True
    for (payload, headers), expected in cases:
        given = list(headers)
        try:
            got = packet_sizes(payload, given)
        except NotImplementedError:
            print("FAIL  packet_sizes is not implemented yet")
            return False
        got_list = list(got) if isinstance(got, (list, tuple)) else got
        if given != headers:
            ok &= _report(f"packet_sizes({payload}, {headers})", False, "changed header_sizes",
                          "build a new list instead of changing the one you were given.")
            continue
        if got_list == expected:
            ok &= _report(f"packet_sizes({payload}, {headers})", True, f"{got_list}", "")
            continue
        if not isinstance(got_list, list) or len(got_list) != len(headers) + 1:
            hint = (f"return a list with one entry more than there are headers "
                    f"({len(headers) + 1} here): the payload first, then one size per layer.")
        elif got_list[0] != payload:
            hint = "the first entry is the payload on its own, before any layer adds a header."
        else:
            hint = ("each layer adds its header to the whole packet it got from the layer above, "
                    "so every entry is the previous entry plus one header.")
        ok &= _report(f"packet_sizes({payload}, {headers})", False, f"returned {got}", hint)
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok


def check_mm7_retry(retry_decision):
    """Checks the retry_decision rule (Lab MM7, part B)."""
    from .twolayer import GIVE_UP, RETRANSMIT, WAIT, normalise_decision, two_layer_link
    groups = [
        ("1 waits for the ACK", [((0, 0, 4, 2), WAIT), ((3, 0, 4, 2), WAIT), ((1, 2, 4, 2), WAIT),
                                 ((1, 0, 2, 0), WAIT)],
         "before `timeout` slots have passed, the ACK may still be on its way: wait."),
        ("2 retransmits after the timeout", [((4, 0, 4, 2), RETRANSMIT), ((5, 1, 4, 2), RETRANSMIT),
                                             ((2, 0, 2, 3), RETRANSMIT), ((9, 0, 4, 2), RETRANSMIT)],
         "once `timeout` slots have passed without an ACK, and the packet has been "
         "retransmitted fewer than max_retransmissions times, send it again."),
        ("3 gives up at the limit", [((4, 2, 4, 2), GIVE_UP), ((2, 0, 2, 0), GIVE_UP),
                                     ((7, 3, 4, 3), GIVE_UP)],
         "when the timeout has passed and the packet has already been retransmitted "
         "max_retransmissions times, stop: return 'give_up'."),
    ]
    ok = True
    for name, cases, hint in groups:
        wrong = []
        for args, expected in cases:
            try:
                raw = retry_decision(*args)
            except NotImplementedError:
                print("FAIL  retry_decision is not implemented yet")
                return False
            if normalise_decision(raw) != expected:
                wrong.append(f"retry_decision{args} returned {raw!r}, expected {expected!r}")
        ok &= _report(name, not wrong, wrong[0] if wrong else f"{len(cases)} cases right", hint)
    if ok:
        r = two_layer_link(retry_decision, reliability="LL", per=0.3, k_ll=2, t_ll=2, n_packets=200,
                           seed=3)
        attempts, last, early = {}, {}, 0
        for e in r.events:
            if e.row == "Zoya LL" and e.kind in ("tx_ok", "tx_lost"):
                attempts[e.label] = attempts.get(e.label, 0) + 1
                if e.label in last and e.slot - last[e.label] < 2:
                    early += 1
                last[e.label] = e.slot
        most = max(attempts.values())
        ok &= _report("4 in the simulator", most <= 3 and early == 0 and r.delivered > 180,
                      f"at most {most} attempts per frame (limit 3), {early} sent before the timeout, "
                      f"{r.delivered}/200 delivered",
                      "run two_layer_link with your rule and look at layer_timeline: are frames "
                      "sent too early, or too often?")
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok
